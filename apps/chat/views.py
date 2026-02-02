"""
Chat API Views
"""
import time
import logging
from django.conf import settings
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer
from apps.rag.services import get_rag_service

logger = logging.getLogger(__name__)


class ConversationListCreateView(generics.ListCreateAPIView):
    """Sohbet listesi ve yeni sohbet oluşturma"""
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Conversation.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ConversationDetailView(generics.RetrieveDestroyAPIView):
    """Sohbet detay ve silme"""
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Conversation.objects.filter(user=self.request.user)


class MessageListView(generics.ListAPIView):
    """Sohbet mesajları listesi"""
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        conversation_id = self.kwargs['pk']
        return Message.objects.filter(
            conversation_id=conversation_id,
            conversation__user=self.request.user
        )


class AskQuestionView(APIView):
    """RAG ile soru sor"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            conversation = Conversation.objects.get(pk=pk, user=request.user)
        except Conversation.DoesNotExist:
            return Response(
                {'error': 'Sohbet bulunamadı'},
                status=status.HTTP_404_NOT_FOUND
            )

        question = request.data.get('question')
        if not question:
            return Response(
                {'error': 'Soru gerekli'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Save user message
        user_message = Message.objects.create(
            conversation=conversation,
            role='user',
            content=question
        )

        # Get RAG response
        start_time = time.time()
        try:
            rag_service = get_rag_service()
            result = rag_service.query(question)
            response_time = int((time.time() - start_time) * 1000)

            # Save assistant message
            assistant_message = Message.objects.create(
                conversation=conversation,
                role='assistant',
                content=result['answer'],
                sources=result['sources'],
                confidence=result['confidence'],
                response_time_ms=response_time
            )

            # Update conversation title if first message
            if conversation.messages.count() == 2:
                conversation.title = question[:50] + ('...' if len(question) > 50 else '')
                conversation.save()

            return Response({
                'message': MessageSerializer(assistant_message).data,
                'user_message': MessageSerializer(user_message).data
            })

        except Exception as e:
            # Log the actual error for debugging
            logger.exception(
                f"RAG query error for user {request.user.id}, "
                f"conversation {pk}: {str(e)}"
            )

            # Sanitized error message for user (don't expose internal details)
            user_error_message = (
                "Üzgünüm, şu anda yanıt oluşturulamıyor. "
                "Lütfen daha sonra tekrar deneyin."
            )

            # Save error message (sanitized)
            Message.objects.create(
                conversation=conversation,
                role='assistant',
                content=user_error_message,
                confidence=0
            )

            # Return sanitized error response
            error_response = {'error': 'Sorgu işlenirken bir hata oluştu.'}
            if settings.DEBUG:
                error_response['debug_message'] = str(e)

            return Response(error_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MessageFeedbackView(APIView):
    """Mesaj geri bildirimi"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            message = Message.objects.get(
                pk=pk,
                conversation__user=request.user,
                role='assistant'
            )
        except Message.DoesNotExist:
            return Response(
                {'error': 'Mesaj bulunamadı'},
                status=status.HTTP_404_NOT_FOUND
            )

        message.is_helpful = request.data.get('is_helpful')
        message.feedback = request.data.get('feedback', '')
        message.save()

        return Response({'message': 'Geri bildirim kaydedildi'})
