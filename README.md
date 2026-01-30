# IOSP - Intelligent Operations & Security Platform

Kurumsal doküman yönetimi ve yapay zeka destekli soru-cevap sistemi. RAG (Retrieval-Augmented Generation) teknolojisi ile şirket içi dokümanlara dayalı akıllı asistan.

## Teknolojiler

| Katman | Teknoloji |
|--------|-----------|
| Backend | Django 5.0, Django REST Framework |
| Veritabanı | PostgreSQL 15 |
| Cache | Redis 7 |
| Vector DB | Qdrant |
| LLM | Ollama (llama2, nomic-embed-text) |
| RAG Pipeline | LangChain |
| Auth | JWT (SimpleJWT) |
| Admin | Jazzmin |
| API Docs | drf-spectacular (OpenAPI 3.0) |

## Özellikler

- **Doküman Yönetimi**: PDF, DOCX, TXT, MD dosya desteği
- **RAG Pipeline**: Dokümanları chunk'lara böler, embedding oluşturur, semantic search yapar
- **Akıllı Sohbet**: Kurumsal dokümanlara dayalı soru-cevap
- **Kullanıcı Yönetimi**: Departman bazlı kullanıcılar, rol tabanlı erişim
- **Audit Log**: Tüm işlemlerin kaydı
- **REST API**: Tam dokümantasyonlu API
- **Modern Admin**: Jazzmin ile şık admin paneli

## Kurulum

### Docker ile (Önerilen)

```bash
# Repoyu klonla
git clone https://github.com/metinemredonmez/is_net.git
cd is_net

# .env dosyasını oluştur
cp .env.example .env

# Servisleri başlat
docker-compose up -d

# Ollama modellerini indir (ilk kurulumda)
docker exec -it iosp-ollama ollama pull llama2
docker exec -it iosp-ollama ollama pull nomic-embed-text
```

### Manuel Kurulum

```bash
# Virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Bağımlılıkları yükle
pip install -r requirements.txt

# Veritabanı migration
python manage.py migrate

# Superuser oluştur
python manage.py createsuperuser

# Sunucuyu başlat
python manage.py runserver
```

## Servisler

| Servis | Port | Açıklama |
|--------|------|----------|
| Django | 8000 | Ana uygulama |
| PostgreSQL | 5432 | Veritabanı |
| Redis | 6379 | Cache & Celery broker |
| Qdrant | 6333 | Vector database |
| Ollama | 11434 | Local LLM |

## API Endpoints

```
POST   /api/auth/token/           # JWT token al
POST   /api/auth/token/refresh/   # Token yenile

GET    /api/documents/            # Doküman listesi
POST   /api/documents/            # Doküman yükle
POST   /api/documents/{id}/process/  # Dokümanı işle (RAG)

GET    /api/chat/conversations/   # Sohbet listesi
POST   /api/chat/conversations/   # Yeni sohbet
POST   /api/chat/conversations/{id}/message/  # Mesaj gönder

POST   /api/rag/query/            # Direkt RAG sorgusu
POST   /api/rag/search/           # Semantic search

GET    /api/docs/                 # Swagger UI
GET    /api/schema/               # OpenAPI schema
```

## Proje Yapısı

```
is_net/
├── apps/
│   ├── accounts/       # Kullanıcı yönetimi
│   ├── documents/      # Doküman yönetimi
│   ├── chat/           # Sohbet modülü
│   └── rag/            # RAG pipeline
├── iosp/
│   ├── settings.py     # Django ayarları
│   ├── urls.py         # URL routing
│   └── wsgi.py
├── data/
│   └── uploads/        # Yüklenen dosyalar
├── static/
├── templates/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── manage.py
```

## Ortam Değişkenleri

```env
# Django
DEBUG=True
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1

# PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=iosp_db
DB_USER=iosp_user
DB_PASSWORD=your-password

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

## Kullanım

### 1. Doküman Yükleme

```bash
curl -X POST http://localhost:8000/api/documents/ \
  -H "Authorization: Bearer <token>" \
  -F "file=@document.pdf" \
  -F "title=Şirket Politikası"
```

### 2. Dokümanı İşleme (RAG Pipeline)

```bash
curl -X POST http://localhost:8000/api/documents/<id>/process/ \
  -H "Authorization: Bearer <token>"
```

### 3. Soru Sorma

```bash
curl -X POST http://localhost:8000/api/rag/query/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"question": "Yıllık izin hakkım kaç gün?"}'
```

## Geliştirme

```bash
# Testleri çalıştır
python manage.py test

# Linting
flake8 .

# Migration oluştur
python manage.py makemigrations
```

## Lisans

MIT License
