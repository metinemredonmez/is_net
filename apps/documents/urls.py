"""
Documents API URLs
"""
from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    path('', views.DocumentListCreateView.as_view(), name='document_list'),
    path('<uuid:pk>/', views.DocumentDetailView.as_view(), name='document_detail'),
    path('<uuid:pk>/process/', views.ProcessDocumentView.as_view(), name='process_document'),
    path('categories/', views.CategoryListView.as_view(), name='category_list'),
]
