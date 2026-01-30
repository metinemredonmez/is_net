"""
Chat API URLs
"""
from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('conversations/', views.ConversationListCreateView.as_view(), name='conversation_list'),
    path('conversations/<uuid:pk>/', views.ConversationDetailView.as_view(), name='conversation_detail'),
    path('conversations/<uuid:pk>/messages/', views.MessageListView.as_view(), name='message_list'),
    path('conversations/<uuid:pk>/ask/', views.AskQuestionView.as_view(), name='ask_question'),
    path('messages/<uuid:pk>/feedback/', views.MessageFeedbackView.as_view(), name='message_feedback'),
]
