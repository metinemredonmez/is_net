#!/bin/bash
# IOSP - Başlatma Scripti

set -e

echo "🚀 IOSP Platform başlatılıyor..."

# .env dosyası kontrolü
if [ ! -f .env ]; then
    echo "❌ HATA: .env dosyası bulunamadı!"
    echo "   Lütfen önce .env.example dosyasını .env olarak kopyalayın:"
    echo "   cp .env.example .env"
    echo "   Ardından güvenli değerler oluşturun:"
    echo "   ./scripts/generate-secrets.sh"
    exit 1
fi

# .env dosyasını yükle
export $(grep -v '^#' .env | xargs)

# 1. Ollama model kontrol
echo "📦 Ollama modelleri kontrol ediliyor..."
docker exec iosp-ollama ollama list 2>/dev/null || true

# Model yoksa indir
if ! docker exec iosp-ollama ollama list 2>/dev/null | grep -q "llama2"; then
    echo "📥 llama2 modeli indiriliyor (bu biraz sürebilir)..."
    docker exec iosp-ollama ollama pull llama2
fi

if ! docker exec iosp-ollama ollama list 2>/dev/null | grep -q "nomic-embed-text"; then
    echo "📥 nomic-embed-text embedding modeli indiriliyor..."
    docker exec iosp-ollama ollama pull nomic-embed-text
fi

echo "✅ Modeller hazır!"

# 2. Django migrations
echo "🔄 Veritabanı migration'ları çalıştırılıyor..."
docker exec iosp-web python manage.py migrate --noinput

# 3. Superuser oluştur (environment variable'lardan)
echo "👤 Admin kullanıcı kontrol ediliyor..."

# Admin credentials kontrolü
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@iosp.local}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-}"

if [ -z "$ADMIN_PASSWORD" ]; then
    # Rastgele şifre oluştur
    ADMIN_PASSWORD=$(openssl rand -base64 16)
    echo "⚠️  ADMIN_PASSWORD tanımlı değil, rastgele şifre oluşturuldu."
fi

docker exec iosp-web python manage.py shell -c "
from apps.accounts.models import User
import os

email = os.environ.get('ADMIN_EMAIL', 'admin@iosp.local')
password = os.environ.get('ADMIN_PASSWORD', '')

if not User.objects.filter(email=email).exists():
    User.objects.create_superuser(
        email=email,
        password=password,
        full_name='IOSP Admin'
    )
    print(f'✅ Admin kullanıcı oluşturuldu: {email}')
else:
    print('ℹ️  Admin kullanıcı zaten mevcut')
"

# 4. Static files
echo "📁 Static dosyalar toplanıyor..."
docker exec iosp-web python manage.py collectstatic --noinput

echo ""
echo "=========================================="
echo "✅ IOSP Platform hazır!"
echo "=========================================="
echo ""
echo "🌐 Admin Panel: http://localhost:8000/admin/"
echo "📚 API Docs:    http://localhost:8000/api/docs/"
echo ""
echo "👤 Giriş Bilgileri:"
echo "   Email:    $ADMIN_EMAIL"
if [ -n "$ADMIN_PASSWORD" ]; then
    echo "   Şifre:    (env ADMIN_PASSWORD'da tanımlı)"
fi
echo ""
echo "⚠️  ÖNEMLİ: Şifreyi .env dosyasında saklayın!"
echo "=========================================="
