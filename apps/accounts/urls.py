"""
Accounts API URLs
"""
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # JWT Auth (rate limited)
    path('token/', views.ThrottledTokenObtainPairView.as_view(), name='token_obtain'),
    path('token/refresh/', views.ThrottledTokenRefreshView.as_view(), name='token_refresh'),

    # User endpoints
    path('me/', views.CurrentUserView.as_view(), name='current_user'),
    path('users/', views.UserListView.as_view(), name='user_list'),
]
