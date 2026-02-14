# Docker Setup and Deployment Guide

This guide provides production-ready Docker architecture for deploying the Legal Tabular Review system.

## Quick Start

### Development Environment

```bash
docker-compose -f docker-compose.dev.yml up -d
# Frontend: http://localhost:5173
# Backend: http://localhost:8000
# pgAdmin: http://localhost:5050 (admin/admin)
```

### Production Environment (Single Server)

```bash
cp ../.env.production ../.env
# Edit .env with strong passwords
docker-compose -f docker-compose.yml up -d
# Application: http://localhost
```

---

## File and Directory Reference

| Component               | Purpose                                           |
| ----------------------- | ------------------------------------------------- |
| Dockerfile.backend      | Production backend image (optimized, minimal)     |
| Dockerfile.frontend     | Production frontend image (Nginx optimization)    |
| Dockerfile.dev          | Development backend (hot reload support)          |
| Dockerfile.frontend.dev | Development frontend (Vite hot reload)            |
| docker-compose.yml      | Production stack (PostgreSQL, Redis, Nginx)       |
| docker-compose.dev.yml  | Development stack (hot reload, pgAdmin)           |
| nginx/                  | Reverse proxy configuration and security settings |
| scripts/                | Utility scripts (health check, backup, restore)   |
| init-db.sql             | Database schema initialization                    |
| DOCKER_GUIDE.md         | Complete deployment guide                         |
| COMMANDS.md             | Command reference                                 |

---

## Architecture Overview

```
┌─────────────────────────────────────────────┐
│          Nginx Reverse Proxy                │ Ports 80/443
│     (Security, Caching, Rate Limit)         │
├─────────────────────────────────────────────┤
│  Frontend (Nginx)  │  Backend (Gunicorn)    │ Separate
│  4 workers, SSL    │  4 workers, health     │ services
│  Port 80/443       │  Port 8000             │
├─────────────────────────────────────────────┤
│  PostgreSQL (12 tables) │  Redis (Cache)    │ Shared
│  Persistent storage     │  Session store    │ services
└─────────────────────────────────────────────┘
```

---

## System Features

### Production Readiness

- Multi-stage builds for minimal image size
- Non-root container execution for enhanced security
- Automated health checks with restart capabilities
- Configured resource limits and quotas
- Gzip compression for optimized bandwidth usage

### Scalability

- Load balancing via Nginx reverse proxy
- Persistent storage for PostgreSQL and Redis
- Horizontal scaling support via docker-compose
- Backup and restore automation

### Security

- HTTPS/TLS support (Let's Encrypt compatible)
- Security headers configuration
- CORS policy enforcement
- Rate limiting capabilities
- Non-root process execution

### Observability

- Health check endpoints
- Structured logging implementation
- Docker health checks

---

## Environment Configuration

### Development (.env.development)

```
LOG_LEVEL=DEBUG
DEBUG_MODE=true
DATABASE_URL=postgresql://reviewer:dev_password@postgres:5432/legal_review_dev
REDIS_URL=redis://redis:6379/0
```

### Production (.env.production)

```
LOG_LEVEL=INFO
DEBUG_MODE=false
DATABASE_URL=postgresql://reviewer:STRONG_PASSWORD@postgres:5432/legal_review
REDIS_URL=redis://redis:6379/0
SECRET_KEY=STRONG_RANDOM_KEY_MIN_32_CHARS
```

---

## 🔄 Service Composition

### Docker Compose (Production)

```yaml
postgres: PostgreSQL 15 (database)
redis: Redis 7 (cache)
backend: Gunicorn + FastAPI
frontend: Nginx (static + React)
nginx: Reverse proxy (SSL, rate limit)
```

---

## 🎯 Performance

| Component       | Dev    | Production                         |
| --------------- | ------ | ---------------------------------- |
| Image Size      | N/A    | ~500MB (backend), ~90MB (frontend) |
| Memory/Instance | 256MB  | 512MB (backend), 128MB (frontend)  |
| CPU/Instance    | 100m   | 250m (backend), 100m (frontend)    |
| Startup Time    | ~10s   | ~15s (first), ~5s (warm)           |
| Response Time   | <300ms | <200ms                             |

---

## 🔐 Security

✅ SSL/TLS ready (HTTP → HTTPS redirect)
✅ Security headers (X-Frame-Options, CSP, etc.)
✅ CORS restricted to known domains
✅ Rate limiting (10 req/s general, 30 req/s API)
✅ Non-root user (appuser, uid 1000)
✅ No hardcoded secrets (environment variables only)
✅ Health checks for availability

---

## 🚀 Deployment Quick Start

### Docker Compose

```bash
# 1. Setup
cp ../env.production ../.env
# Edit .env with production values

# 2. Build
docker-compose -f docker-compose.yml build

# 3. Start
docker-compose -f docker-compose.yml up -d

# 4. Monitor
docker-compose ps
docker-compose logs -f backend
```

---

## 🛠️ Operations

### Backup Database

```bash
bash scripts/backup-db.sh
# Creates: /backups/legal_review/backup_YYYYMMDD_HHMMSS.sql.gz
```

### View Logs

```bash
docker-compose logs -f backend
docker-compose logs --tail=100 backend
```

### Scale Services

```bash
docker-compose up -d --scale backend=3
# Load balanced by Nginx
```

### Restart Service

```bash
docker-compose restart backend
docker-compose down && docker-compose up -d
```

---

## 📊 Volumes

| Volume        | Size  | Contents           |
| ------------- | ----- | ------------------ |
| postgres_data | 50GB  | Database files     |
| redis_data    | 10GB  | Cache/session data |
| uploads_pvc   | 100GB | Uploaded documents |
| nginx_logs    | 5GB   | Access/error logs  |

---

## Health Monitoring

Each service has automated health checks:

```bash
# Docker Compose
docker-compose ps
# Shows STATUS (healthy/unhealthy)

# Manual API check
curl http://localhost:8000/health
# Returns: {"status": "healthy"}
```

---

## Operations and Troubleshooting

### Service won't start

```bash
docker-compose logs backend
# Check error message
docker-compose build --no-cache backend
```

### Database connection error

```bash
docker-compose exec postgres psql -U reviewer legal_review
# Test PostgreSQL connection directly
```

### Slow performance

```bash
docker stats
# Check CPU/memory usage
docker-compose logs --tail=50 backend
# Check for errors in logs
```

### Disk full

```bash
docker system prune -a
# Clean unused images/containers
du -sh docker/*
# Check volume sizes
```

---

## Reference Documentation

- **DOCKER_GUIDE.md** - Complete guide (100+ lines)
- **COMMANDS.md** - Command reference (40+ lines)
- **../docs/DEPLOYMENT.md** - Cloud deployment options
- **../DEPLOYMENT_CHECKLIST.md** - Pre-launch checklist

---

## 🎓 Learning Resources

1. **First Time?** → Start with `docker-compose.dev.yml` (development)
2. **Deploy?** → Follow `DOCKER_GUIDE.md` (step-by-step)
3. **Operate?** → Reference `COMMANDS.md` (quick lookup)
4. **Production?** → Check `../DEPLOYMENT_CHECKLIST.md`

---

## ✅ Status

| Component     | Status   | Notes                    |
| ------------- | -------- | ------------------------ |
| Backend       | ✅ Ready | All services implemented |
| Frontend      | ✅ Ready | All pages implemented    |
| PostgreSQL    | ✅ Ready | Schema auto-created      |
| Redis         | ✅ Ready | Caching configured       |
| Nginx         | ✅ Ready | Reverse proxy configured |
| Monitoring    | ✅ Ready | Health checks enabled    |
| Security      | ✅ Ready | Headers, rate limit, TLS |
| Documentation | ✅ Ready | Complete guides included |

---

## 🚀 Next Steps

1. **Choose Environment**
   - Development → Use `docker-compose.dev.yml`
   - Production → Use `docker-compose.yml`

2. **Setup**
   - Copy environment file
   - Configure secrets
   - Build/deploy

3. **Verify**
   - Services running
   - Health checks passing
   - API responding

4. **Monitor**
   - Check logs
   - Monitor resources
   - Setup alerts

---

**Ready to deploy? Start with:** `docker-compose up -d` for development or `docker-compose -f docker-compose.yml up -d` for production
