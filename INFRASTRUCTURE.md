# Flight Tracker - Infrastructure & Deployment

This document describes the infrastructure and deployment configuration for the Flight Price Tracker application.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Kubernetes Cluster                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │  FastAPI    │  │   Celery    │  │   Celery    │          │
│  │    API      │  │   Worker    │  │    Beat     │          │
│  │  (x2-x10)   │  │   (x2-x20)  │  │    (x1)     │          │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘          │
│         │                │                │                  │
│         └────────────────┼────────────────┘                  │
│                          │                                   │
│         ┌────────────────┼────────────────┐                  │
│         │                │                │                  │
│  ┌──────▼──────┐  ┌──────▼──────┐         │                  │
│  │  PostgreSQL │  │    Redis    │         │                  │
│  │    RDS      │  │ ElastiCache │         │                  │
│  │  (HA Multi-AZ)│ (Cluster Mode)│        │                  │
│  └─────────────┘  └─────────────┘         │                  │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Local Development with Docker Compose

```bash
# Copy environment template
cp .env.example .env

# Update .env with your configuration
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

### Access Services

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Flower (Monitoring)**: http://localhost:5555 (run with `--profile monitoring`)

## Docker Compose Services

| Service | Image | Port | Description |
|---------|-------|------|-------------|
| postgres | postgres:15-alpine | 5432 | PostgreSQL database |
| redis | redis:7-alpine | 6379 | Redis cache & message broker |
| api | Custom FastAPI | 8000 | FastAPI application |
| worker | Custom Celery | - | Celery worker for background tasks |
| beat | Custom Celery | - | Celery beat for scheduled tasks |
| flower | Custom Celery | 5555 | Celery monitoring (optional) |

## Kubernetes Deployment

### Prerequisites

- Kubernetes cluster (EKS, GKE, AKS, or local with kind/minikube)
- kubectl configured
- Helm 3.x (optional)
- Kustomize (built into kubectl)

### Deploy with Kustomize

```bash
# Staging environment
kubectl apply -k k8s/overlays/staging/

# Production environment
kubectl apply -k k8s/overlays/production/

# View resources
kubectl get all -n flight-tracker-staging
```

### Deploy to EKS (using Terraform)

```bash
# Navigate to terraform directory
cd terraform/

# Initialize Terraform
terraform init

# Plan staging deployment
terraform plan -var-file=staging.tfvars

# Apply staging deployment
terraform apply -var-file=staging.tfvars

# Configure kubectl
aws eks update-kubeconfig --name flight-tracker-staging --region us-east-1

# Deploy application
kubectl apply -k ../k8s/overlays/staging/
```

## CI/CD Pipeline

### GitHub Actions Workflows

1. **CI/CD Pipeline** (`.github/workflows/ci-cd.yml`)
   - Runs tests on every push/PR
   - Builds and pushes Docker images
   - Deploys to staging on `develop` branch
   - Deploys to production on version tags

2. **Security Scan** (`.github/workflows/security-scan.yml`)
   - Dependency vulnerability scanning
   - Trivy security scans
   - Docker image scanning

3. **Dependabot** (`.github/dependabot.yml`)
   - Automated dependency updates
   - Weekly updates for Python, Docker, and GitHub Actions

### Required Secrets

Configure these secrets in GitHub repository settings:

```
STAGING_KUBECONFIG        # Kubernetes config for staging
PRODUCTION_KUBECONFIG     # Kubernetes config for production
DOCKER_REGISTRY_USERNAME  # Container registry username
DOCKER_REGISTRY_TOKEN     # Container registry token
```

## Environment Configuration

### Required Environment Variables

```bash
# Application
ENVIRONMENT=production
SECRET_KEY=<generate-strong-random-key>
CORS_ORIGINS=https://yourdomain.com

# Database
POSTGRES_USER=flighttracker
POSTGRES_PASSWORD=<strong-password>
POSTGRES_DB=flight_tracker
DATABASE_URL=postgresql://user:pass@host:5432/db

# Redis
REDIS_URL=redis://host:6379/0

# Flight APIs (optional)
AVIATION_STACK_API_KEY=<your-key>
AMADEUS_API_KEY=<your-key>
AMADEUS_API_SECRET=<your-secret>
```

## Monitoring & Observability

### Health Checks

- `/api/v1/health/live` - Liveness probe
- `/api/v1/health/ready` - Readiness probe with dependency checks

### Celery Monitoring

- Flower dashboard for task monitoring
- Prometheus metrics (coming soon)
- CloudWatch Logs integration

### Recommended Add-ons

1. **Prometheus + Grafana** - Metrics and dashboards
2. **Jaeger/Tempo** - Distributed tracing
3. **Loki** - Log aggregation
4. **Alertmanager** - Alerting

## Scaling

### Horizontal Pod Autoscaler (HPA)

The production configuration includes HPA for automatic scaling:

- **API**: 3-20 replicas based on CPU/memory
- **Worker**: 3-20 replicas based on CPU/memory

### Manual Scaling

```bash
# Scale API deployment
kubectl scale deployment flight-tracker-api --replicas=5 -n flight-tracker-production

# Scale worker deployment
kubectl scale deployment flight-tracker-worker --replicas=10 -n flight-tracker-production
```

## Backup & Disaster Recovery

### Database Backups

- **RDS Automated Backups**: Enabled (7-30 days retention)
- **Manual Snapshots**: Before major deployments
- **Point-in-time Recovery**: Available for RDS

### Redis Backups

- **ElastiCache Snapshots**: Automated daily snapshots
- **Backup Window**: 03:00-06:00 UTC

### Recovery Procedures

1. **Database Restore**: Use RDS point-in-time recovery
2. **Redis Restore**: Restore from ElastiCache snapshot
3. **Application Rollback**: Use previous Docker image tag

## Security

### Best Practices Implemented

- ✅ Non-root containers
- ✅ Read-only root filesystem (where possible)
- ✅ Network policies (coming soon)
- ✅ Secrets management via Kubernetes Secrets
- ✅ TLS/SSL for ingress
- ✅ Security scanning in CI/CD

### Additional Recommendations

1. Enable Pod Security Policies/Standards
2. Implement network policies
3. Use AWS Secrets Manager or HashiCorp Vault
4. Enable EKS audit logging
5. Implement OPA/Gatekeeper policies

## Cost Optimization

### Staging Environment

- Uses Spot instances for EKS nodes
- Single NAT gateway
- Smaller instance sizes
- Reduced replica counts

### Production Environment

- On-demand instances for reliability
- Multi-AZ for high availability
- Auto-scaling for cost efficiency
- Reserved instances for predictable workloads

## Troubleshooting

### Common Issues

**Pod won't start:**
```bash
kubectl describe pod <pod-name> -n flight-tracker
kubectl logs <pod-name> -n flight-tracker
```

**Database connection issues:**
```bash
# Check database connectivity
kubectl exec -it <pod-name> -n flight-tracker -- python -c "import psycopg2; psycopg2.connect('...')"
```

**Celery worker not processing tasks:**
```bash
# Check worker logs
kubectl logs -l app=flight-tracker-worker -n flight-tracker

# Inspect Celery cluster
kubectl exec -it <worker-pod> -n flight-tracker -- celery -A app.core.celery inspect active
```

## Support

For issues or questions:
- Check existing GitHub issues
- Review application logs
- Contact the development team
