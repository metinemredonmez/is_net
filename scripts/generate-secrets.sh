#!/bin/bash
# IOSP - Güvenli Secret Oluşturucu
# Bu script .env dosyasındaki placeholder değerleri güvenli rastgele değerlerle değiştirir

set -e

ENV_FILE=".env"
ENV_EXAMPLE=".env.example"

echo "🔐 IOSP Secrets Generator"
echo "========================="
echo ""

# .env dosyası var mı kontrol et
if [ ! -f "$ENV_FILE" ]; then
    if [ -f "$ENV_EXAMPLE" ]; then
        echo "📋 .env.example'dan .env oluşturuluyor..."
        cp "$ENV_EXAMPLE" "$ENV_FILE"
    else
        echo "❌ .env.example bulunamadı!"
        exit 1
    fi
fi

# Güvenli rastgele string oluştur
generate_secret() {
    openssl rand -base64 48 | tr -dc 'a-zA-Z0-9' | head -c $1
}

generate_password() {
    openssl rand -base64 24 | tr -dc 'a-zA-Z0-9!@#$%' | head -c $1
}

echo "🔑 Güvenli değerler oluşturuluyor..."
echo ""

# SECRET_KEY oluştur
SECRET_KEY=$(generate_secret 50)
echo "✅ SECRET_KEY oluşturuldu"

# DB_PASSWORD oluştur
DB_PASSWORD=$(generate_password 24)
echo "✅ DB_PASSWORD oluşturuldu"

# ADMIN_PASSWORD oluştur
ADMIN_PASSWORD=$(generate_password 16)
echo "✅ ADMIN_PASSWORD oluşturuldu"

# .env dosyasını güncelle
echo ""
echo "📝 .env dosyası güncelleniyor..."

# macOS ve Linux uyumlu sed
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s|^SECRET_KEY=.*|SECRET_KEY=$SECRET_KEY|" "$ENV_FILE"
    sed -i '' "s|^DB_PASSWORD=.*|DB_PASSWORD=$DB_PASSWORD|" "$ENV_FILE"
    sed -i '' "s|^ADMIN_PASSWORD=.*|ADMIN_PASSWORD=$ADMIN_PASSWORD|" "$ENV_FILE"
else
    # Linux
    sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$SECRET_KEY|" "$ENV_FILE"
    sed -i "s|^DB_PASSWORD=.*|DB_PASSWORD=$DB_PASSWORD|" "$ENV_FILE"
    sed -i "s|^ADMIN_PASSWORD=.*|ADMIN_PASSWORD=$ADMIN_PASSWORD|" "$ENV_FILE"
fi

echo ""
echo "=========================================="
echo "✅ Secrets başarıyla oluşturuldu!"
echo "=========================================="
echo ""
echo "📁 Dosya: $ENV_FILE"
echo ""
echo "⚠️  ÖNEMLİ UYARILAR:"
echo "   1. .env dosyasını ASLA git'e commit etmeyin!"
echo "   2. Production'da bu değerleri güvenli bir yerde saklayın"
echo "   3. Şifreleri başkalarıyla paylaşmayın"
echo ""
echo "🚀 Artık projeyi başlatabilirsiniz:"
echo "   docker-compose up -d"
echo "   ./scripts/start.sh"
echo "=========================================="
