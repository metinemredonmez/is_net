"""
Documents API Views
"""
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Document, DocumentCategory
from .serializers import DocumentSerializer, DocumentCategorySerializer
from apps.core.throttling import UploadRateThrottle


class DocumentListCreateView(generics.ListCreateAPIView):
    """Doküman listesi ve yükleme"""
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [permissions.IsAuthenticated]

    def get_throttles(self):
        """POST (upload) için özel throttle uygula"""
        if self.request.method == 'POST':
            return [UploadRateThrottle()]
        return super().get_throttles()

    def get_queryset(self):
        qs = super().get_queryset()
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category__slug=category)
        # Filter by status
        doc_status = self.request.query_params.get('status')
        if doc_status:
            qs = qs.filter(status=doc_status)
        return qs

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)


class DocumentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Doküman detay, güncelleme, silme"""
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]


class ProcessDocumentView(APIView):
    """Dokümanı işle (embedding oluştur)"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            document = Document.objects.get(pk=pk)
            # TODO: Celery task ile async işleme
            document.status = 'processing'
            document.save()
            return Response({'message': 'Doküman işleme kuyruğuna alındı'})
        except Document.DoesNotExist:
            return Response({'error': 'Doküman bulunamadı'}, status=status.HTTP_404_NOT_FOUND)


class CategoryListView(generics.ListAPIView):
    """Kategori listesi"""
    queryset = DocumentCategory.objects.all()
    serializer_class = DocumentCategorySerializer
    permission_classes = [permissions.IsAuthenticated]
