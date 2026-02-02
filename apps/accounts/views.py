"""
Accounts API Views
"""
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .models import User
from .serializers import UserSerializer
from apps.core.throttling import LoginRateThrottle


class ThrottledTokenObtainPairView(TokenObtainPairView):
    """
    JWT Token endpoint with rate limiting.
    Brute-force koruması için dakikada 5 deneme limiti.
    """
    throttle_classes = [LoginRateThrottle]


class ThrottledTokenRefreshView(TokenRefreshView):
    """
    JWT Token refresh endpoint with rate limiting.
    """
    throttle_classes = [LoginRateThrottle]


class CurrentUserView(APIView):
    """Mevcut kullanıcı bilgisi"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class UserListView(generics.ListAPIView):
    """Kullanıcı listesi (sadece admin/manager)"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]
