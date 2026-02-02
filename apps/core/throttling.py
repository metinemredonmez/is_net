"""
IOSP - Custom Throttling Classes
Rate limiting for API protection
"""
from rest_framework.throttling import SimpleRateThrottle


class LoginRateThrottle(SimpleRateThrottle):
    """
    Login endpoint için özel throttle.
    Brute-force saldırılarını engellemek için dakikada 5 deneme.
    IP bazlı throttling.
    """
    scope = 'login'

    def get_cache_key(self, request, view):
        # IP bazlı throttling (anonim ve authenticated için)
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request)
        }


class UploadRateThrottle(SimpleRateThrottle):
    """
    Dosya yükleme endpoint'i için özel throttle.
    Saatte 10 dosya yükleme limiti.
    Kullanıcı bazlı throttling.
    """
    scope = 'upload'

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)

        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }


class RAGQueryRateThrottle(SimpleRateThrottle):
    """
    RAG query endpoint'i için özel throttle.
    Dakikada 30 sorgu limiti.
    LLM maliyetlerini kontrol altında tutmak için.
    """
    scope = 'rag_query'

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)

        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }


class BurstRateThrottle(SimpleRateThrottle):
    """
    Ani yoğun istekleri engellemek için burst throttle.
    Saniyede 10 istek limiti.
    """
    scope = 'burst'
    rate = '10/second'

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)

        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }
