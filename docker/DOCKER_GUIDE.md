# Docker Setup & Production Deployment Guide

## Directory Structure

```
docker/
├── Dockerfile.backend           # Production backend image
├── Dockerfile.frontend          # Production frontend image
├── Dockerfile.dev               # Development backend image
├── Dockerfile.frontend.dev      # Development frontend image
├── docker-compose.yml           # Production compose (with PostgreSQL, Redis)
├── docker-compose.dev.yml       # Development compose (with hot reload)
├── nginx/
│   ├── nginx.conf               # Main Nginx configuration
│   └── conf.d/
│       └── default.conf         # Server block configuration
├── scripts/
│   ├── healthcheck-backend.sh   # Health check script
│   ├── backup-db.sh             # Database backup script
│   └── restore-db.sh            # Database restore script
└── init-db.sql                  # Database initialization script
```

---

## Quick Start: Development

```bash
# 1. Copy development env file
cp .env.development .env

# 2. Start all services
docker-compose -f docker/docker-compose.dev.yml up -d

# 3. Initialize database
docker-compose -f docker/docker-compose.dev.yml exec backend python -c \
  "from src.storage.repository import DatabaseRepository; DatabaseRepository()"

# 4. Access services
# Frontend: http://localhost:5173
# Backend: http://localhost:8000
# API Docs: http://localhost:8000/docs
# pgAdmin: http://localhost:5050 (admin@example.com / admin)
```

---

## Quick Start: Production

```bash
# 1. Copy production env file and edit
cp .env.production .env

# 2. Set strong passwords in .env
# DATABASE_URL, POSTGRES_PASSWORD, SECRET_KEY

# 3. Build images
docker-compose -f docker/docker-compose.yml build

# 4. Start services
docker-compose -f docker/docker-compose.yml up -d

# 5. Verify services
docker-compose -f docker/docker-compose.yml ps

# 6. Check logs
docker-compose -f docker/docker-compose.yml logs -f backend
```

---

## Service Details

### PostgreSQL

- **Container**: legal_review_db
- **Port**: 5432 (internal), 5432 (mapped)
- **Database**: legal_review
- **User**: reviewer
- **Password**: From .env POSTGRES_PASSWORD
- **Volumes**: postgres_data (50GB recommended)
- **Health**: Checked via pg_isready

### Redis

- **Container**: legal_review_cache
- **Port**: 6379
- **Use**: Session cache, async task queue
- **Volumes**: redis_data

### Backend API

- **Container**: legal_review_backend
- **Port**: 8000
- **Workers**: 4 (via gunicorn)
- **Timeout**: 120 seconds
- **Health**: http://localhost:8000/health
- **API Docs**: http://localhost:8000/docs

### Frontend

- **Container**: legal_review_frontend
- **Port**: 3000 (mapped) / 80 (internal)
- **Build**: Multi-stage (node builder + nginx)
- **Assets**: Cached for 1 year
- **Compression**: Gzip enabled

### Nginx Reverse Proxy

- **Container**: legal_review_proxy
- **Ports**: 80 (HTTP), 443 (HTTPS)
- **Features**: SSL/TLS, rate limiting, compression, security headers
- **Cache**: Browser cache for static assets
- **Logs**: nginx_logs volume

---

## Operations Guide

### Restart Services

```bash
# Restart specific service
docker-compose restart backend

# Restart all services
docker-compose restart

# Full rebuild and restart
docker-compose down
docker-compose up -d
```

### View Logs

```bash
# Real-time logs
docker-compose logs -f backend

# Last 100 lines
docker-compose logs --tail=100 backend

# All services
docker-compose logs -f
```

### Database Operations

**Backup Database**

```bash
docker-compose exec postgres pg_dump -U reviewer legal_review | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

**Restore Database**

```bash
gunzip < backup_20240115_120000.sql.gz | docker-compose exec -T postgres psql -U reviewer legal_review
```

**Access Database Shell**

```bash
docker-compose exec postgres psql -U reviewer -d legal_review
```

### Scale Services

```bash
# Scale backend to 3 instances
docker-compose up -d --scale backend=3

# Note: Load balance with Nginx (already configured)
```

---

## Production Best Practices

### 1. Environment Variables

- ✓ Use .env.production (never commit to git)
- ✓ Rotate secrets regularly
- ✓ Use strong, random passwords (min 32 chars)
- ✓ Enable SSL/TLS certificates

### 2. Database

- ✓ Use PostgreSQL (not SQLite)
- ✓ Enable backups (daily recommended)
- ✓ Monitor disk space (50GB+ for production)
- ✓ Enable encryption at rest

### 3. Security

- ✓ Nginx reverse proxy with rate limiting
- ✓ Security headers configured
- ✓ CORS restricted to known domains
- ✓ Non-root user in containers
- ✓ Health checks enabled

### 4. Monitoring

- ✓ Container health checks
- ✓ Log aggregation (ELK, Datadog, CloudWatch)
- ✓ Alerts for errors and high CPU/memory

### 5. Scaling

- ✓ Manual scaling via docker-compose --scale
- ✓ Load balancer in front (Nginx, AWS ALB)
- ✓ Stateless backend services
- ✓ Shared Redis for caching

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs backend

# Rebuild image
docker-compose build --no-cache backend

# Check resource constraints
docker stats
```

### Database Connection Error

```bash
# Check if PostgreSQL is healthy
docker-compose ps postgres

# Test connection
docker-compose exec postgres pg_isready -U reviewer

# Check connection string in .env
echo $DATABASE_URL
```

### Slow Performance

```bash
# Monitor resource usage
docker stats

# Check database indexes
docker-compose exec postgres psql -U reviewer legal_review -c "\di"

# Monitor network
docker network inspect docker_legal_review_network
```

### Disk Space Issues

```bash
# Check disk usage
df -h

# Clean up unused images/volumes
docker image prune -a
docker volume prune

# Backup and delete old data
./docker/scripts/backup-db.sh
```

---

## SSL/TLS for Production

### Option 1: Let's Encrypt with Nginx (Docker Compose)

```bash
# Install Certbot
apt-get install certbot python3-certbot-nginx

# Get certificate
certbot certonly --standalone -d yourdomain.com

# Copy to docker ssl directory
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem docker/ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem docker/ssl/
sudo chown 1000:1000 docker/ssl/*
```

---

## Backup & Disaster Recovery

### Automated Backups (Cron)

```bash
# Add to crontab
0 2 * * * /path/to/docker/scripts/backup-db.sh >> /var/log/backups.log 2>&1

# Upload to S3
aws s3 sync /backups/legal_review s3://your-backup-bucket/
```

### Manual Restore

```bash
# List backups
ls -lh /backups/legal_review/

# Restore specific backup
./docker/scripts/restore-db.sh /backups/legal_review/backup_20240115_020000.sql.gz
```

---

## Monitoring Stack (Optional)

```yaml
# Add to docker-compose.yml for monitoring
prometheus:
  image: prom/prometheus:latest
  volumes:
    - ./docker/prometheus.yml:/etc/prometheus/prometheus.yml
  ports:
    - "9090:9090"

grafana:
  image: grafana/grafana:latest
  ports:
    - "3001:3000"
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=admin
```

---

##Performance Tuning

### PostgreSQL

```sql
-- Increase shared buffers (in docker-compose environment section)
# POSTGRES_INIT_ARGS: "-c shared_buffers=256MB -c effective_cache_size=1GB"

-- Create indexes
CREATE INDEX idx_extraction_status ON extraction_results(status);
CREATE INDEX idx_review_status ON review_states(status);
```

### Redis

- Monitor with `redis-cli info`
- Increase memory if needed
- Configure eviction policy

### Backend

- Increase workers: `WORKERS=8` (for high load)
- Adjust timeout: `WORKER_TIMEOUT=300`
- Enable caching (Redis)

---

## Next Steps

1. **Configure Domain**: Update Nginx config with your domain
2. **Set Strong Passwords**: Edit .env.production
3. **Setup SSL**: Follow SSL/TLS section
4. **Deploy**: Use docker-compose
5. **Monitor**: Setup logging and alerting
6. **Backup**: Configure automated backups
