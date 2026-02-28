# Deployment Guide 🚀

This guide covers deployment options for the Flight Price Tracker.

## Table of Contents

1. [Docker Compose (Recommended)](#docker-compose-recommended)
2. [Production Considerations](#production-considerations)
3. [Environment Variables](#environment-variables)
4. [Monitoring & Maintenance](#monitoring--maintenance)

---

## Docker Compose (Recommended)

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 2GB RAM minimum
- 10GB disk space

### Quick Deploy

```bash
# Clone repository
git clone https://github.com/builderbuilds123/flight-tracker.git
cd flight-tracker

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Start all services
docker-compose up -d

# Verify deployment
docker-compose ps
curl http://localhost:8000/api/v1/health
```

### Services Overview

| Service | Port | Description |
|---------|------|-------------|
| api | 8000 | FastAPI application |
| worker | - | Celery worker for price checks |
| beat | - | Celery Beat scheduler |
| telegram-bot | - | Telegram notification bot |
| db | 5432 | PostgreSQL database |
| redis | 6379 | Redis cache & message broker |

### Access Points

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

---

## Production Considerations

### 1. Security

**Update Default Passwords:**
```env
POSTGRES_PASSWORD=your_secure_password_here
```

**Restrict CORS:**
```env
CORS_ORIGINS=["https://yourdomain.com"]
```

**Enable HTTPS:**
- Use a reverse proxy (Nginx, Traefik)
- Obtain SSL certificate (Let's Encrypt)

**Example Nginx Configuration:**
```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 2. Resource Limits

Update `docker-compose.yml`:
```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
```

### 3. Database Backups

**Automated Backups:**
```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
docker exec flight-tracker-db pg_dump -U postgres flight_tracker > /backups/flight_tracker_$DATE.sql
# Keep only last 7 days
find /backups -name "flight_tracker_*.sql" -mtime +7 -delete
```

**Cron Job (daily at 2 AM):**
```cron
0 2 * * * /path/to/backup.sh
```

### 4. Scaling

**Horizontal Scaling:**
- Run multiple worker instances:
```bash
docker-compose up -d --scale worker=3
```

**Load Balancing:**
- Use Nginx or HAProxy in front of multiple API instances

### 5. Logging

**Centralized Logging:**
```yaml
# docker-compose.yml
services:
  api:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

**Log Aggregation:**
- ELK Stack (Elasticsearch, Logstash, Kibana)
- Grafana Loki
- CloudWatch Logs

---

## Environment Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `KIWI_API_KEY` | Kiwi.com API key | `your_api_key` |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | `123456:ABC-DEF1234` |

### Database

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_USER` | `postgres` | Database username |
| `POSTGRES_PASSWORD` | `postgres` | Database password |
| `POSTGRES_DB` | `flight_tracker` | Database name |
| `POSTGRES_HOST` | `db` | Database host |
| `POSTGRES_PORT` | `5432` | Database port |

### Redis

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | `redis` | Redis host |
| `REDIS_PORT` | `6379` | Redis port |

### Application

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `false` | Debug mode |
| `CORS_ORIGINS` | `*` | Allowed origins |
| `PRICE_CHECK_INTERVAL_HOURS` | `6` | Default check interval |

---

## Monitoring & Maintenance

### Health Checks

```bash
# API health
curl http://localhost:8000/api/v1/health

# Database connectivity
docker exec flight-tracker-db pg_isready -U postgres

# Redis connectivity
docker exec flight-tracker-redis redis-cli ping
```

### Log Monitoring

```bash
# Real-time logs
docker-compose logs -f

# API logs only
docker-compose logs -f api

# Last 100 lines
docker-compose logs --tail=100 api
```

### Database Maintenance

**Vacuum and Analyze:**
```bash
docker exec flight-tracker-db psql -U postgres -d flight_tracker -c "VACUUM ANALYZE;"
```

**Check Table Sizes:**
```bash
docker exec flight-tracker-db psql -U postgres -d flight_tracker -c "
SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"
```

### Price History Cleanup

Add to `docker-compose.yml`:
```yaml
services:
  cleanup:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    command: >
      psql -h db -U postgres -d flight_tracker -c
      "DELETE FROM price_history WHERE found_at < NOW() - INTERVAL '90 days';"
    schedule: "0 0 * * 0"  # Weekly
```

---

## Troubleshooting

### Common Issues

**1. Container won't start**
```bash
# Check logs
docker-compose logs api

# Verify environment
docker-compose config

# Rebuild
docker-compose up -d --build
```

**2. Database connection errors**
```bash
# Restart database
docker-compose restart db

# Check database status
docker-compose exec db pg_isready -U postgres
```

**3. Redis connection errors**
```bash
# Restart Redis
docker-compose restart redis

# Test connection
docker-compose exec redis redis-cli ping
```

**4. Celery tasks not executing**
```bash
# Check worker logs
docker-compose logs worker

# Restart worker and beat
docker-compose restart worker beat
```

### Getting Help

- Check logs: `docker-compose logs -f`
- Review documentation: [README.md](README.md)
- Open an issue on GitHub

---

## Updates

### Updating the Application

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose up -d --build

# Run migrations (if any)
docker-compose exec api alembic upgrade head
```

### Database Migrations

```bash
# Check current migration
docker-compose exec api alembic current

# Upgrade to latest
docker-compose exec api alembic upgrade head

# Downgrade one version
docker-compose exec api alembic downgrade -1
```

---

**Deployment Support**: Open an issue on GitHub for assistance.
