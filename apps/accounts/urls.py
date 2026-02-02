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

    # Registration & Logout
    path('register/', views.RegisterView.as_view(), name='register'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('logout-all/', views.LogoutAllView.as_view(), name='logout_all'),

    # Password Management
    path('password/change/', views.PasswordChangeView.as_view(), name='password_change'),
    path('password/reset/', views.PasswordResetRequestView.as_view(), name='password_reset'),
    path('password/reset/confirm/', views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),

    # User endpoints
    path('me/', views.CurrentUserView.as_view(), name='current_user'),
    path('users/', views.UserListView.as_view(), name='user_list'),
]
