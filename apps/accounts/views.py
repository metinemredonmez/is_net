"""
Accounts API Views
"""
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken

from .models import User, UserActivity
from .serializers import (
    UserSerializer,
    UserRegistrationSerializer,
    PasswordChangeSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
)
from apps.core.throttling import LoginRateThrottle

logger = logging.getLogger(__name__)


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


class RegisterView(generics.CreateAPIView):
    """
    Kullanıcı kayıt endpoint'i.

    POST /api/auth/register/
    - Email benzersizlik kontrolü
    - Güvenli parola validasyonu (min 8 karakter, büyük/küçük harf, rakam)
    - Yeni kullanıcılar 'viewer' rolü ile oluşturulur
    """
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [LoginRateThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # JWT token oluştur
        refresh = RefreshToken.for_user(user)

        logger.info(f"New user registered: {user.email}")

        return Response({
            'message': 'Kayıt başarılı.',
            'user': UserSerializer(user).data,
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }
        }, status=status.HTTP_201_CREATED)


class LogoutView(APIView):
    """
    Güvenli çıkış endpoint'i.
    Refresh token'ı blacklist'e ekler.

    POST /api/auth/logout/
    Body: {"refresh": "token_string"}
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if not refresh_token:
                return Response(
                    {'error': 'Refresh token gerekli.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            token = RefreshToken(refresh_token)
            token.blacklist()

            # Aktivite logu
            UserActivity.objects.create(
                user=request.user,
                activity_type='logout',
                description='Kullanıcı çıkış yaptı',
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            )

            logger.info(f"User logged out: {request.user.email}")

            return Response(
                {'message': 'Çıkış başarılı.'},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.warning(f"Logout failed for user {request.user.email}: {e}")
            return Response(
                {'error': 'Çıkış işlemi başarısız.'},
                status=status.HTTP_400_BAD_REQUEST
            )

    def _get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


class LogoutAllView(APIView):
    """
    Tüm cihazlardan çıkış endpoint'i.
    Kullanıcının tüm refresh token'larını blacklist'e ekler.

    POST /api/auth/logout-all/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            # Kullanıcının tüm outstanding token'larını al
            tokens = OutstandingToken.objects.filter(user=request.user)
            for token in tokens:
                # Zaten blacklist'te değilse ekle
                BlacklistedToken.objects.get_or_create(token=token)

            logger.info(f"User logged out from all devices: {request.user.email}")

            return Response(
                {'message': 'Tüm cihazlardan çıkış yapıldı.'},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.warning(f"Logout all failed for user {request.user.email}: {e}")
            return Response(
                {'error': 'Çıkış işlemi başarısız.'},
                status=status.HTTP_400_BAD_REQUEST
            )


class PasswordChangeView(APIView):
    """
    Parola değiştirme endpoint'i.

    POST /api/auth/password/change/
    Body: {"old_password": "...", "new_password": "...", "new_password_confirm": "..."}
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        # Parolayı değiştir
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()

        # Tüm token'ları geçersiz kıl (güvenlik için)
        tokens = OutstandingToken.objects.filter(user=user)
        for token in tokens:
            BlacklistedToken.objects.get_or_create(token=token)

        # Yeni token oluştur
        refresh = RefreshToken.for_user(user)

        logger.info(f"Password changed for user: {user.email}")

        return Response({
            'message': 'Parola başarıyla değiştirildi.',
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }
        }, status=status.HTTP_200_OK)


class PasswordResetRequestView(APIView):
    """
    Parola sıfırlama isteği endpoint'i.
    Email gönderir (şimdilik token döndürür).

    POST /api/auth/password/reset/
    Body: {"email": "user@example.com"}
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']

        # Kullanıcıyı bul
        try:
            user = User.objects.get(email__iexact=email)

            # Token oluştur
            token = secrets.token_urlsafe(32)

            # Token'ı cache'e kaydet (1 saat geçerli)
            cache_key = f"password_reset_{token}"
            cache.set(cache_key, user.id, timeout=3600)

            # TODO: Email gönder
            # send_password_reset_email(user.email, token)

            logger.info(f"Password reset requested for: {email}")

            # Geliştirme ortamında token'ı döndür
            if settings.DEBUG:
                return Response({
                    'message': 'Parola sıfırlama bağlantısı e-posta adresinize gönderildi.',
                    'debug_token': token,  # Sadece DEBUG modda
                }, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            # Güvenlik: Kullanıcı var mı yok mu bilgisini verme
            logger.warning(f"Password reset requested for non-existent email: {email}")

        # Her durumda aynı yanıtı ver (enumeration saldırılarına karşı)
        return Response({
            'message': 'Eğer bu e-posta adresi kayıtlıysa, parola sıfırlama bağlantısı gönderildi.',
        }, status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    """
    Parola sıfırlama onay endpoint'i.

    POST /api/auth/password/reset/confirm/
    Body: {"token": "...", "new_password": "...", "new_password_confirm": "..."}
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data['token']
        cache_key = f"password_reset_{token}"

        # Token'ı doğrula
        user_id = cache.get(cache_key)
        if not user_id:
            return Response(
                {'error': 'Geçersiz veya süresi dolmuş token.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(id=user_id)

            # Parolayı değiştir
            user.set_password(serializer.validated_data['new_password'])
            user.save()

            # Token'ı sil
            cache.delete(cache_key)

            # Eski token'ları geçersiz kıl
            tokens = OutstandingToken.objects.filter(user=user)
            for t in tokens:
                BlacklistedToken.objects.get_or_create(token=t)

            logger.info(f"Password reset completed for user: {user.email}")

            return Response({
                'message': 'Parola başarıyla sıfırlandı. Yeni parolanızla giriş yapabilirsiniz.',
            }, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response(
                {'error': 'Geçersiz token.'},
                status=status.HTTP_400_BAD_REQUEST
            )


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
