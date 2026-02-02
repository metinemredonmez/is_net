"""
IOSP - Custom Exception Handler
Hata mesajlarını standartlaştırır ve güvenli hale getirir.
"""
import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler for DRF.
    - Standart hata formatı
    - Production'da detaylı hata mesajlarını gizler
    - Tüm hataları loglar
    """
    # DRF'in default handler'ını çağır
    response = exception_handler(exc, context)

    # Request bilgilerini al
    request = context.get('request')
    view = context.get('view')

    # Hata detaylarını logla
    log_data = {
        'exception_type': type(exc).__name__,
        'exception_message': str(exc),
        'view': view.__class__.__name__ if view else 'Unknown',
        'path': request.path if request else 'Unknown',
        'method': request.method if request else 'Unknown',
        'user': str(request.user) if request and hasattr(request, 'user') else 'Anonymous',
    }

    if response is not None:
        # DRF tarafından yakalanan hatalar
        log_data['status_code'] = response.status_code
        logger.warning(f"API Error: {log_data}")

        # Throttling hatası için özel mesaj
        if response.status_code == 429:
            response.data = {
                'success': False,
                'error': {
                    'code': 'RATE_LIMIT_EXCEEDED',
                    'message': 'Çok fazla istek gönderildi. Lütfen biraz bekleyin.',
                    'retry_after': response.get('Retry-After', 60)
                }
            }
        else:
            # Standart hata formatı
            error_detail = response.data

            # Production'da detaylı hata mesajlarını gizle
            if not settings.DEBUG:
                if response.status_code >= 500:
                    error_detail = 'Sunucu hatası oluştu. Lütfen daha sonra tekrar deneyin.'

            response.data = {
                'success': False,
                'error': {
                    'code': get_error_code(response.status_code),
                    'message': get_error_message(error_detail),
                    'details': error_detail if settings.DEBUG else None
                }
            }
    else:
        # DRF tarafından yakalanmayan hatalar (500 errors)
        logger.exception(f"Unhandled API Error: {log_data}")

        response = Response(
            {
                'success': False,
                'error': {
                    'code': 'INTERNAL_SERVER_ERROR',
                    'message': 'Beklenmeyen bir hata oluştu.' if not settings.DEBUG else str(exc),
                    'details': str(exc) if settings.DEBUG else None
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return response


def get_error_code(status_code):
    """HTTP status kodundan hata kodu oluştur"""
    error_codes = {
        400: 'BAD_REQUEST',
        401: 'UNAUTHORIZED',
        403: 'FORBIDDEN',
        404: 'NOT_FOUND',
        405: 'METHOD_NOT_ALLOWED',
        409: 'CONFLICT',
        422: 'VALIDATION_ERROR',
        429: 'RATE_LIMIT_EXCEEDED',
        500: 'INTERNAL_SERVER_ERROR',
        502: 'BAD_GATEWAY',
        503: 'SERVICE_UNAVAILABLE',
    }
    return error_codes.get(status_code, 'ERROR')


def get_error_message(error_detail):
    """Hata detayından okunabilir mesaj oluştur"""
    if isinstance(error_detail, str):
        return error_detail
    elif isinstance(error_detail, dict):
        # DRF validation hataları
        if 'detail' in error_detail:
            return str(error_detail['detail'])
        # Field-level hatalar
        messages = []
        for field, errors in error_detail.items():
            if isinstance(errors, list):
                messages.append(f"{field}: {', '.join(str(e) for e in errors)}")
            else:
                messages.append(f"{field}: {errors}")
        return '; '.join(messages) if messages else 'Bir hata oluştu'
    elif isinstance(error_detail, list):
        return '; '.join(str(e) for e in error_detail)
    return 'Bir hata oluştu'
