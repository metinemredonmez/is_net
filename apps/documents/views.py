"""
Documents API Views
"""
from django.db.models import Q
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Document, DocumentCategory
from .serializers import DocumentSerializer, DocumentCategorySerializer
from apps.core.throttling import UploadRateThrottle
from apps.core.permissions import (
    IsOwnerOrAdminOrPublic,
    CanUploadDocuments,
)


class DocumentListCreateView(generics.ListCreateAPIView):
    """
    Doküman listesi ve yükleme.

    GET: Kullanıcının erişebildiği dokümanları listeler
    - Admin/Manager: Tüm dokümanlar
    - Diğer roller: Kendi yüklediği + public dokümanlar

    POST: Yeni doküman yükle (Admin, Manager, Analyst, Operator)
    """
    serializer_class = DocumentSerializer
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [permissions.IsAuthenticated, CanUploadDocuments]

    def get_throttles(self):
        """POST (upload) için özel throttle uygula"""
        if self.request.method == 'POST':
            return [UploadRateThrottle()]
        return super().get_throttles()

    def get_queryset(self):
        """
        Kullanıcının erişebildiği dokümanları filtrele.
        Admin/Manager: Tüm dokümanlar
        Diğerleri: Kendi yüklediği + public
        """
        user = self.request.user

        # Admin veya Manager tüm dokümanları görebilir
        if user.is_staff or user.role in ['admin', 'manager']:
            qs = Document.objects.all()
        else:
            # Diğer kullanıcılar: kendi dokümanları + public
            qs = Document.objects.filter(
                Q(uploaded_by=user) | Q(is_public=True)
            )

        # Query optimizasyonu
        qs = qs.select_related('category', 'uploaded_by')

        # Filtreleme
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category__slug=category)

        doc_status = self.request.query_params.get('status')
        if doc_status:
            qs = qs.filter(status=doc_status)

        return qs.order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)


class DocumentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Doküman detay, güncelleme, silme.

    Erişim kontrolü:
    - GET: Sahibi, Admin, Manager veya public ise erişebilir
    - PUT/PATCH/DELETE: Sadece sahibi veya Admin
    """
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdminOrPublic]

    def get_queryset(self):
        """
        Kullanıcının erişebildiği dokümanları filtrele.
        """
        user = self.request.user

        if user.is_staff or user.role in ['admin', 'manager']:
            return Document.objects.all()

        return Document.objects.filter(
            Q(uploaded_by=user) | Q(is_public=True)
        ).select_related('category', 'uploaded_by')

    def perform_update(self, serializer):
        """Güncelleme için sahiplik kontrolü"""
        instance = self.get_object()
        user = self.request.user

        # Sadece sahibi veya admin güncelleyebilir
        if not (user.is_staff or user.role == 'admin' or instance.uploaded_by == user):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Bu dokümanı güncelleme yetkiniz yok.")

        serializer.save()

    def perform_destroy(self, instance):
        """Silme için sahiplik kontrolü"""
        user = self.request.user

        # Sadece sahibi veya admin silebilir
        if not (user.is_staff or user.role == 'admin' or instance.uploaded_by == user):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Bu dokümanı silme yetkiniz yok.")

        instance.delete()


class ProcessDocumentView(APIView):
    """
    Dokümanı işle (embedding oluştur).
    Sadece doküman sahibi veya admin işleyebilir.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            document = Document.objects.get(pk=pk)
        except Document.DoesNotExist:
            return Response(
                {'error': 'Doküman bulunamadı'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Yetki kontrolü
        user = request.user
        if not (user.is_staff or user.role in ['admin', 'manager'] or document.uploaded_by == user):
            return Response(
                {'error': 'Bu dokümanı işleme yetkiniz yok'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Zaten işlenmiş mi kontrol et
        if document.status == 'completed':
            return Response(
                {'message': 'Doküman zaten işlenmiş', 'status': document.status},
                status=status.HTTP_200_OK
            )

        if document.status == 'processing':
            return Response(
                {'message': 'Doküman şu anda işleniyor', 'status': document.status},
                status=status.HTTP_200_OK
            )

        # TODO: Celery task ile async işleme
        document.status = 'processing'
        document.save()

        return Response({
            'message': 'Doküman işleme kuyruğuna alındı',
            'document_id': str(document.id),
            'status': document.status
        })


class CategoryListView(generics.ListAPIView):
    """Kategori listesi"""
    queryset = DocumentCategory.objects.all()
    serializer_class = DocumentCategorySerializer
    permission_classes = [permissions.IsAuthenticated]
