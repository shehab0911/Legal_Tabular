# Quick Docker Compose Commands

## Development Environment

```bash
# Start development environment
docker-compose -f docker/docker-compose.dev.yml up -d

# View logs
docker-compose -f docker/docker-compose.dev.yml logs -f

# Stop all services
docker-compose -f docker/docker-compose.dev.yml down

# Remove volumes (careful - deletes data)
docker-compose -f docker/docker-compose.dev.yml down -v

# Rebuild images
docker-compose -f docker/docker-compose.dev.yml build --no-cache

# Access shell
docker-compose -f docker/docker-compose.dev.yml exec backend bash
docker-compose -f docker/docker-compose.dev.yml exec frontend sh
```

## Production Environment

```bash
# Start production environment
docker-compose -f docker/docker-compose.yml up -d

# View logs
docker-compose -f docker/docker-compose.yml logs -f backend

# Stop all services
docker-compose -f docker/docker-compose.yml down

# Update services
docker-compose -f docker/docker-compose.yml pull
docker-compose -f docker/docker-compose.yml up -d

# Scale services
docker-compose -f docker/docker-compose.yml up -d --scale backend=3
```

## Database Operations

```bash
# Backup database
docker-compose exec postgres pg_dump -U reviewer legal_review > backup.sql

# Restore database
docker-compose exec -T postgres psql -U reviewer legal_review < backup.sql

# Database shell
docker-compose exec postgres psql -U reviewer -d legal_review

# List databases
docker-compose exec postgres psql -U reviewer -l
```

## Monitoring

```bash
# View container status
docker-compose ps

# View resource usage
docker stats

# View logs for specific service
docker-compose logs backend

# Follow logs
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail=100
```

## Troubleshooting

```bash
# Check service health
docker-compose ps

# Restart specific service
docker-compose restart backend

# Rebuild and restart
docker-compose up --build -d

# Full reset
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d

# Check network
docker network ls
docker network inspect docker_legal_review_network
```
