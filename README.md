# IOSP - Intelligent Operations & Security Platform

Kurumsal doküman yönetimi ve yapay zeka destekli soru-cevap sistemi. RAG (Retrieval-Augmented Generation) teknolojisi ile şirket içi dokümanlara dayalı akıllı asistan.

## Özellikler

- 🔐 **Güvenli Kimlik Doğrulama**: JWT tabanlı auth, rol bazlı erişim kontrolü
- 📄 **Doküman Yönetimi**: PDF, DOCX, TXT, MD dosya desteği
- 🤖 **AI Asistan**: RAG tabanlı akıllı soru-cevap sistemi
- 📊 **Dashboard**: Gerçek zamanlı istatistikler ve raporlar
- 🔄 **Async İşleme**: Celery ile arka plan görevleri
- 📈 **Monitoring**: Prometheus + Grafana ile izleme
- 🔒 **Güvenlik**: Rate limiting, input validasyonu, CORS

## Teknolojiler

### Backend
| Katman | Teknoloji |
|--------|-----------|
| Framework | Django 5.0, Django REST Framework |
| Veritabanı | PostgreSQL 15 |
| Cache | Redis 7 |
| Async Tasks | Celery |
| Vector DB | ChromaDB |
| LLM | OpenAI API |
| RAG Pipeline | LangChain |
| Auth | JWT (SimpleJWT) |
| Admin | Jazzmin |
| API Docs | drf-spectacular (OpenAPI 3.0) |

### Frontend
| Katman | Teknoloji |
|--------|-----------|
| Framework | Next.js 15 (App Router) |
| Language | TypeScript |
| Styling | Tailwind CSS + shadcn/ui |
| State | Zustand |
| HTTP | Axios |

### DevOps
| Katman | Teknoloji |
|--------|-----------|
| Containerization | Docker & Docker Compose |
| CI/CD | GitHub Actions |
| Reverse Proxy | Nginx |
| SSL | Let's Encrypt |
| Monitoring | Prometheus + Grafana |

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

# .env dosyasını oluştur ve güvenli secret'lar generate et
cp .env.example .env
chmod +x scripts/generate-secrets.sh
./scripts/generate-secrets.sh

# Servisleri başlat
docker-compose up -d

# Platform kurulumunu tamamla (migration, admin user, models)
chmod +x scripts/start.sh
./scripts/start.sh
```

> **Güvenlik Notu:** `.env` dosyası hassas bilgiler içerir. Asla git'e commit etmeyin!

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
# Backend testleri
pytest --cov=apps --cov-report=html

# Frontend testleri
cd frontend && npm run test

# Linting
ruff check .
cd frontend && npm run lint

# Migration oluştur
python manage.py makemigrations
```

## Frontend Geliştirme

```bash
cd frontend

# Bağımlılıkları yükle
npm install

# Development server
npm run dev

# Production build
npm run build

# Testler
npm run test
```

## CI/CD Pipeline

### Continuous Integration
- Backend ve frontend testleri
- Linting ve security scans
- Docker build test

```bash
# CI workflow trigger
git push origin develop
```

### Continuous Deployment
- Staging: develop branch'ine push
- Production: tag oluşturma (v*.*.*)

```bash
# Staging deploy
git push origin develop

# Production deploy
git tag v1.0.0
git push origin v1.0.0
```

## Monitoring

```bash
# Monitoring stack'i başlat
docker compose -f docker-compose.monitoring.yml up -d

# Erişim
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3001 (admin/admin)
```

## Backup & Restore

```bash
# Manual backup
./scripts/backup.sh manual

# Scheduled backup (cron ile)
./scripts/backup.sh scheduled

# Backup'ları listele
./scripts/restore.sh list

# Database restore
./scripts/restore.sh postgres /path/to/backup.sql.gz

# Media restore
./scripts/restore.sh media /path/to/backup.tar.gz

# Rollback
./scripts/rollback.sh quick
```

## Production Deployment

```bash
# Production compose ile başlat
docker compose -f docker-compose.prod.yml up -d

# Migrations
docker compose -f docker-compose.prod.yml exec backend python manage.py migrate

# Static files
docker compose -f docker-compose.prod.yml exec backend python manage.py collectstatic

# SSL sertifikası (Let's Encrypt)
docker compose run --rm certbot certonly --webroot -w /var/www/certbot \
    -d iosp.example.com -d api.iosp.example.com
```

## Güvenlik

- JWT token authentication with refresh tokens
- Rate limiting on API endpoints (10 req/s general, 5 req/min login)
- File upload validation (MIME type, size, extension)
- CORS configuration
- SQL injection protection (Django ORM)
- XSS protection (React escaping)
- CSRF protection
- Secure headers (HSTS, X-Frame-Options, etc.)

## Lisans

MIT License
