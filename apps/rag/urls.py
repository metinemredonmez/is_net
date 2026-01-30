"""
RAG API URLs
"""
from django.urls import path
from . import views

app_name = 'rag'

urlpatterns = [
    path('query/', views.RAGQueryView.as_view(), name='query'),
    path('process/<uuid:document_id>/', views.ProcessDocumentView.as_view(), name='process'),
    path('search/', views.SemanticSearchView.as_view(), name='search'),
    path('health/', views.HealthCheckView.as_view(), name='health'),
]
