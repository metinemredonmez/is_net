#!/bin/bash
# IOSP - Başlatma Scripti

set -e

echo "🚀 IOSP Platform başlatılıyor..."

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

# 3. Superuser oluştur
echo "👤 Admin kullanıcı kontrol ediliyor..."
docker exec iosp-web python manage.py shell -c "
from apps.accounts.models import User
if not User.objects.filter(email='admin@isnet.com.tr').exists():
    User.objects.create_superuser(
        email='admin@isnet.com.tr',
        password='admin123',
        full_name='IOSP Admin'
    )
    print('✅ Admin kullanıcı oluşturuldu: admin@isnet.com.tr / admin123')
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
echo "   Email:    admin@isnet.com.tr"
echo "   Şifre:    admin123"
echo ""
echo "=========================================="
