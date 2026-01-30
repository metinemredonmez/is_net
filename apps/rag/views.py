"""
RAG API Views
"""
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from .services import get_rag_service
import logging

logger = logging.getLogger(__name__)


class RAGQueryView(APIView):
    """
    RAG Query Endpoint
    Dokümanlardan soru-cevap
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="RAG Query",
        description="Yüklenen dokümanlardan soru-cevap",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "Sorulacak soru"},
                    "k": {"type": "integer", "default": 5, "description": "Kaç kaynak kullanılsın"}
                },
                "required": ["question"]
            }
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "answer": {"type": "string"},
                    "sources": {"type": "array"},
                    "confidence": {"type": "number"}
                }
            }
        }
    )
    def post(self, request):
        question = request.data.get('question')
        k = request.data.get('k', 5)

        if not question:
            return Response(
                {'error': 'Soru gerekli'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            rag_service = get_rag_service()
            result = rag_service.query(question, k=k)

            # Log activity
            from apps.accounts.models import UserActivity
            UserActivity.objects.create(
                user=request.user,
                activity_type='chat_query',
                description=question[:200],
                ip_address=request.META.get('REMOTE_ADDR'),
                metadata={'confidence': result['confidence']}
            )

            return Response(result)

        except Exception as e:
            logger.error(f"RAG query hatası: {e}")
            return Response(
                {'error': 'Sorgulama sırasında hata oluştu'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProcessDocumentView(APIView):
    """Doküman işleme (embedding oluştur)"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, document_id):
        try:
            rag_service = get_rag_service()
            result = rag_service.process_document(str(document_id))

            if result['success']:
                return Response({
                    'message': 'Doküman başarıyla işlendi',
                    'chunk_count': result['chunk_count']
                })
            else:
                return Response(
                    {'error': result.get('error', 'İşleme hatası')},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            logger.error(f"Doküman işleme hatası: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SemanticSearchView(APIView):
    """Semantic search endpoint"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        query = request.query_params.get('q')
        k = int(request.query_params.get('k', 5))

        if not query:
            return Response(
                {'error': 'Arama sorgusu gerekli (q parametresi)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            rag_service = get_rag_service()
            results = rag_service.vector_store.search(query, k=k)
            return Response({'results': results})

        except Exception as e:
            logger.error(f"Search hatası: {e}")
            return Response(
                {'error': 'Arama hatası'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class HealthCheckView(APIView):
    """RAG servisi health check"""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        health = {
            'status': 'healthy',
            'services': {}
        }

        # Check Ollama
        try:
            import httpx
            from django.conf import settings
            response = httpx.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=5)
            health['services']['ollama'] = 'up' if response.status_code == 200 else 'down'
        except:
            health['services']['ollama'] = 'down'

        # Check Qdrant
        try:
            from qdrant_client import QdrantClient
            from django.conf import settings
            client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT, timeout=5)
            client.get_collections()
            health['services']['qdrant'] = 'up'
        except:
            health['services']['qdrant'] = 'down'

        # Overall status
        if 'down' in health['services'].values():
            health['status'] = 'degraded'

        return Response(health)
