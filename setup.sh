#!/bin/bash
# IS-NET Proje Kurulum Script
# Claude tarafından oluşturuldu

echo "=== IS-NET Kurulum Başlıyor ==="

# Repository klonla (eğer yoksa)
if [ ! -d ".git" ]; then
    git clone https://github.com/metinemredonmez/is_net.git
    cd is_net
fi

# Python virtual environment oluştur
python3 -m venv venv
source venv/bin/activate

# Bağımlılıkları yükle
pip install --upgrade pip
pip install -r requirements.txt

# Environment dosyasını kopyala
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "⚠️  .env dosyasını düzenlemeyi unutmayın!"
fi

# Veritabanı migration
python manage.py migrate

# Static dosyaları topla
python manage.py collectstatic --noinput

echo "=== Kurulum Tamamlandı ==="
echo "Çalıştırmak için: python manage.py runserver"
