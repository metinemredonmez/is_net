"""
Documents API URLs
"""
from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    # Document CRUD
    path('', views.DocumentListCreateView.as_view(), name='document_list'),
    path('<uuid:pk>/', views.DocumentDetailView.as_view(), name='document_detail'),

    # Processing endpoints
    path('<uuid:pk>/process/', views.ProcessDocumentView.as_view(), name='process_document'),
    path('<uuid:pk>/status/', views.DocumentStatusView.as_view(), name='document_status'),
    path('<uuid:pk>/reprocess/', views.ReprocessDocumentView.as_view(), name='reprocess_document'),

    # Categories
    path('categories/', views.CategoryListView.as_view(), name='category_list'),
]
