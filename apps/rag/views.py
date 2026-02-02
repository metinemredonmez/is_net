"""
RAG API Views
"""
from django.conf import settings
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from .services import get_rag_service
from apps.core.throttling import RAGQueryRateThrottle
import logging
import httpx

logger = logging.getLogger(__name__)


class RAGQueryView(APIView):
    """
    RAG Query Endpoint
    Dokümanlardan soru-cevap
    """
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [RAGQueryRateThrottle]

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
            logger.exception(f"RAG query error for user {request.user.id}: {e}")
            error_response = {'error': 'Sorgulama sırasında hata oluştu'}
            if settings.DEBUG:
                error_response['debug_message'] = str(e)
            return Response(error_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
                # Log internal error but return sanitized message
                logger.error(f"Document processing failed: {result.get('error')}")
                error_response = {'error': 'Doküman işlenirken bir hata oluştu'}
                if settings.DEBUG:
                    error_response['debug_message'] = result.get('error')
                return Response(error_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            logger.exception(f"Document processing error for {document_id}: {e}")
            error_response = {'error': 'Doküman işlenirken beklenmeyen bir hata oluştu'}
            if settings.DEBUG:
                error_response['debug_message'] = str(e)
            return Response(error_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SemanticSearchView(APIView):
    """Semantic search endpoint"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        query = request.query_params.get('q')
        k_param = request.query_params.get('k', '5')

        if not query:
            return Response(
                {'error': 'Arama sorgusu gerekli (q parametresi)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            k = int(k_param)
        except ValueError:
            return Response(
                {'error': 'k parametresi geçerli bir sayı olmalı'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            rag_service = get_rag_service()
            results = rag_service.vector_store.search(query, k=k)
            return Response({'results': results})

        except Exception as e:
            logger.exception(f"Semantic search error: {e}")
            error_response = {'error': 'Arama sırasında bir hata oluştu'}
            if settings.DEBUG:
                error_response['debug_message'] = str(e)
            return Response(error_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
            response = httpx.get(
                f"{settings.OLLAMA_BASE_URL}/api/tags",
                timeout=5.0
            )
            health['services']['ollama'] = 'up' if response.status_code == 200 else 'down'
        except httpx.RequestError as e:
            logger.warning(f"Ollama health check failed: {e}")
            health['services']['ollama'] = 'down'
        except Exception as e:
            logger.error(f"Unexpected error checking Ollama: {e}")
            health['services']['ollama'] = 'error'

        # Check Qdrant
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http.exceptions import UnexpectedResponse

            client = QdrantClient(
                host=settings.QDRANT_HOST,
                port=settings.QDRANT_PORT,
                timeout=5.0
            )
            client.get_collections()
            health['services']['qdrant'] = 'up'
        except UnexpectedResponse as e:
            logger.warning(f"Qdrant health check failed: {e}")
            health['services']['qdrant'] = 'down'
        except ConnectionError as e:
            logger.warning(f"Qdrant connection failed: {e}")
            health['services']['qdrant'] = 'down'
        except Exception as e:
            logger.error(f"Unexpected error checking Qdrant: {e}")
            health['services']['qdrant'] = 'error'

        # Overall status
        service_statuses = health['services'].values()
        if 'error' in service_statuses:
            health['status'] = 'unhealthy'
        elif 'down' in service_statuses:
            health['status'] = 'degraded'

        return Response(health)
