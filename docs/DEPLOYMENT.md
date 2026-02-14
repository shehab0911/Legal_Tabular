# Deployment & Operations Guide

## 1. LOCAL DEVELOPMENT SETUP

### 1.1 Prerequisites

**Python 3.10+**

```bash
python --version  # Should be 3.10 or higher
```

**Node.js 18+**

```bash
node --version   # Should be 18+
npm --version    # Should be 9+
```

**PostgreSQL 14+ (Optional - for production)**

```bash
psql --version   # For production deployment only
```

### 1.2 Backend Setup

**Clone and navigate to backend:**

```bash
cd backend
```

**Create virtual environment:**

```bash
python -m venv venv

# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate
```

**Install dependencies:**

```bash
pip install -r requirements.txt
```

**Create .env file:**

```bash
# .env
DATABASE_URL=sqlite:///./legal_review.db
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:5173
DEBUG_MODE=true
```

**Initialize database:**

```bash
python -c "from src.storage.repository import DatabaseRepository; DatabaseRepository()"
```

**Run backend:**

```bash
uvicorn app:app --reload --port 8000
```

Backend API available at: `http://localhost:8000`
OpenAPI docs at: `http://localhost:8000/docs`

### 1.3 Frontend Setup

**Navigate to frontend:**

```bash
cd frontend
```

**Install dependencies:**

```bash
npm install
```

**Create .env file:**

```bash
# .env.local
VITE_API_URL=http://localhost:8000/api
```

**Run development server:**

```bash
npm run dev
```

Frontend available at: `http://localhost:5173`

---

## 2. DOCKER DEPLOYMENT

### 2.1 Docker Compose (Local + Development)

**Create docker-compose.yml:**

```yaml
version: "3.8"

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: legal_review
      POSTGRES_USER: reviewer
      POSTGRES_PASSWORD: secure_password_change_me
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://reviewer:secure_password_change_me@postgres:5432/legal_review
      LOG_LEVEL: DEBUG
    depends_on:
      - postgres
    volumes:
      - ./backend:/app
    command: uvicorn app:app --host 0.0.0.0 --reload

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    ports:
      - "5173:5173"
    environment:
      VITE_API_URL: http://localhost:8000/api
    volumes:
      - ./frontend:/app
    command: npm run dev

volumes:
  postgres_data:
```

**Backend Dockerfile:**

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Frontend Dockerfile (Development):**

```dockerfile
# frontend/Dockerfile.dev
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host"]
```

**Frontend Dockerfile (Production):**

```dockerfile
# frontend/Dockerfile.prod
FROM node:18-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

**nginx.conf for frontend:**

```nginx
# frontend/nginx.conf
server {
    listen 80;
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://backend:8000/api/;
    }
}
```

**Run locally with Docker Compose:**

```bash
docker-compose up

# In another terminal, initialize database:
docker-compose exec backend python -c "from src.storage.repository import DatabaseRepository; DatabaseRepository('postgresql://...')"

# Access frontend at http://localhost:5173
# Access backend at http://localhost:8000
# Access API docs at http://localhost:8000/docs
```

---

## 3. CLOUD DEPLOYMENT

### 3.1 AWS EC2 Deployment

**EC2 Configuration:**

- Instance type: t3.medium (2 CPU, 4GB RAM minimum)
- OS: Ubuntu 22.04 LTS
- Security Group: Open ports 80, 443, 22

**SSH into instance:**

```bash
ssh -i key.pem ubuntu@your-instance-ip
```

**Install dependencies:**

```bash
# System packages
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3-pip nginx postgresql postgresql-contrib nodejs npm docker.io docker-compose

# Add ubuntu to docker group
sudo usermod -aG docker ubuntu
```

**Clone repository and deploy:**

```bash
git clone https://github.com/yourorg/legal-tabular-review.git
cd legal-tabular-review
docker-compose -f docker-compose.prod.yml up -d
```

**Set up Nginx reverse proxy:**

```nginx
# /etc/nginx/sites-available/legal-review
upstream backend {
    server 127.0.0.1:8000;
}

upstream frontend {
    server 127.0.0.1:5173;
}

server {
    listen 80;
    server_name yourdomain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name yourdomain.com;

    # SSL certificates (use Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # Frontend
    location / {
        proxy_pass http://frontend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Backend API
    location /api/ {
        proxy_pass http://backend/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Obtain SSL certificate with Let's Encrypt:**

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot certonly --standalone -d yourdomain.com
```

### 3.2 Heroku Deployment

**Create Procfile:**

```
# Root Procfile
web: cd backend && gunicorn app:app --workers 4 --bind 0.0.0.0:$PORT
release: python -c "from src.storage.repository import DatabaseRepository; DatabaseRepository()"
```

**Create .buildpacks:**

```
https://github.com/heroku/heroku-buildpack-python.git
https://github.com/heroku/heroku-buildpack-nodejs.git
```

**Deploy:**

```bash
heroku login
heroku create your-app-name
heroku config:set DATABASE_URL=postgresql://...
git push heroku main
heroku logs --tail
```

---

## 4. PRODUCTION CONFIGURATION

### 4.1 Environment Variables

**Backend (.env):**

```bash
# Database
DATABASE_URL=postgresql://user:password@host:5432/legal_review

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# API
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
API_TIMEOUT=300

# LLM (if using external API)
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4

# Security
SECRET_KEY=your-secret-key-min-32-chars
ALGORITHM=HS256
TOKEN_EXPIRY=3600

# Document upload
MAX_UPLOAD_SIZE=104857600  # 100MB
ALLOWED_FORMATS=pdf,docx,txt,html

# Performance
WORKER_THREADS=4
DATABASE_POOL_SIZE=20
```

**Frontend (.env.production):**

```bash
VITE_API_URL=https://yourdomain.com/api
VITE_LOG_LEVEL=warn
VITE_ENABLE_ANALYTICS=true
```

### 4.2 Database Migration (SQLite → PostgreSQL)

**1. Create PostgreSQL database:**

```bash
sudo -u postgres psql
CREATE DATABASE legal_review;
CREATE USER reviewer WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE legal_review TO reviewer;
\q
```

**2. Generate migration script:**

```python
# scripts/migrate_db.py
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.schema import CreateTable

# Export schema from SQLite
sqlite_engine = create_engine('sqlite:///./legal_review.db')
sqlite_metadata = MetaData()
sqlite_metadata.reflect(bind=sqlite_engine)

# Create in PostgreSQL
pg_engine = create_engine('postgresql://reviewer:password@localhost/legal_review')

for table in sqlite_metadata.sorted_tables:
    sql = CreateTable(table)
    pg_engine.execute(sql)

print("Schema migrated successfully")
```

**3. Migrate data:**

```bash
python scripts/migrate_db.py
```

### 4.3 Monitoring & Logging

**Application Logging (backend):**

```python
# backend/src/logging_config.py
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
        }
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        return json.dumps(log_data)

def setup_logging(log_level='INFO'):
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level))

    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)

    return logger
```

**Add to backend/app.py:**

```python
from src.logging_config import setup_logging

logger = setup_logging(os.getenv('LOG_LEVEL', 'INFO'))

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    logger.info({
        'method': request.method,
        'path': request.url.path,
        'status_code': response.status_code,
        'process_time': process_time,
    })

    return response
```

**Monitoring Dashboard (sample metrics):**

```python
# backend/src/metrics.py
from prometheus_client import Counter, Histogram, Gauge
import time

# Request metrics
request_count = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration')

# Document processing
documents_processed = Counter('documents_processed_total', 'Total documents processed')
extraction_accuracy = Gauge('extraction_accuracy', 'Last extraction accuracy score')

# Error tracking
errors_total = Counter('errors_total', 'Total errors', ['error_type'])
```

### 4.4 Backup Strategy

**Automated daily backup (PostgreSQL):**

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backups/legal_review"
DB_NAME="legal_review"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Create backup
pg_dump -U reviewer $DB_NAME > "$BACKUP_DIR/backup_$TIMESTAMP.sql"

# Compress
gzip "$BACKUP_DIR/backup_$TIMESTAMP.sql"

# Upload to S3
aws s3 cp "$BACKUP_DIR/backup_$TIMESTAMP.sql.gz" s3://your-bucket/backups/

# Clean up old backups (keep 30 days)
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +30 -delete

echo "Backup completed: backup_$TIMESTAMP.sql.gz"
```

**Add to crontab:**

```bash
# Run daily at 2 AM
0 2 * * * /path/to/backup.sh >> /var/log/backup.log 2>&1
```

---

## 5. SCALING & PERFORMANCE

### 5.1 Database Optimization

**Add indexes (PostgreSQL):**

```sql
-- Improve extraction queries
CREATE INDEX idx_extraction_project_id ON extraction_result(project_id);
CREATE INDEX idx_extraction_document_id ON extraction_result(document_id);
CREATE INDEX idx_extraction_status ON extraction_result(status);

-- Improve review queries
CREATE INDEX idx_review_project_id ON review_state(project_id);
CREATE INDEX idx_review_status ON review_state(status);

-- Improve citation queries
CREATE INDEX idx_citation_extraction_id ON citation(extraction_id);
```

**Enable connection pooling (pgBouncer):**

```ini
# /etc/pgbouncer/pgbouncer.ini
[databases]
legal_review = host=localhost port=5432 dbname=legal_review

[pgbouncer]
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 25
reserve_pool_size = 5
```

### 5.2 Caching Strategy

**Redis for session caching:**

```python
# backend/src/cache.py
import redis
import json

class CacheService:
    def __init__(self, redis_url='redis://localhost:6379'):
        self.client = redis.from_url(redis_url)

    def set_extraction_result(self, extraction_id, data, ttl=3600):
        key = f"extraction:{extraction_id}"
        self.client.setex(key, ttl, json.dumps(data))

    def get_extraction_result(self, extraction_id):
        key = f"extraction:{extraction_id}"
        data = self.client.get(key)
        return json.loads(data) if data else None
```

### 5.3 Load Balancing

**Nginx Load Balancer:**

```nginx
upstream backend_servers {
    server backend1:8000;
    server backend2:8000;
    server backend3:8000;
    least_conn;  # Least connections algorithm
}

server {
    listen 80;
    location /api {
        proxy_pass http://backend_servers;
        proxy_next_upstream error timeout invalid_header http_500 http_502 http_503;
    }
}
```

---

## 6. TROUBLESHOOTING

### Database Connection Issues

```bash
# Check PostgreSQL connection
psql -h localhost -U reviewer -d legal_review -c "SELECT 1"

# Check connection pool
SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname;
```

### High Memory Usage

```bash
# Check Python memory
ps aux | grep python
free -h

# Check database cache
sudo su - postgres -c "psql -c 'SHOW shared_buffers;'"
```

### Slow API Responses

```bash
# Check slow queries
grep -i "slow" /var/log/postgresql/postgresql.log | head -20

# Run ANALYZE on tables
python -c "from src.storage.repository import DatabaseRepository; DatabaseRepository().analyze_tables()"
```

### Deployment Rollback

```bash
# Docker Compose
docker-compose down
git revert HEAD
docker-compose up -d
```

---

## Summary

**Development**: Docker Compose with PostgreSQL for realistic environment
**Staging**: AWS EC2 with Nginx, SSL, automated backups
**Production**: Docker Compose with optimization, monitoring, load balancing
**Database**: PostgreSQL in production, SQLite for development
**Monitoring**: Structured logging, metrics collection, error tracking
**Backups**: Daily automated backups with 30-day retention
