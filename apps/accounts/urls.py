"""
Accounts API URLs
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

app_name = 'accounts'

urlpatterns = [
    # JWT Auth
    path('token/', TokenObtainPairView.as_view(), name='token_obtain'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # User endpoints
    path('me/', views.CurrentUserView.as_view(), name='current_user'),
    path('users/', views.UserListView.as_view(), name='user_list'),
]
