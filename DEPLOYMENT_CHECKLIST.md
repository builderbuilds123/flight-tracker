# Deployment Checklist

## ✅ Completed Infrastructure Setup

### Docker & Local Development
- [x] Docker Compose with all services (PostgreSQL, Redis, FastAPI, Celery worker, Celery beat)
- [x] Dockerfile for FastAPI application
- [x] Dockerfile.worker for Celery worker
- [x] Dockerfile.beat for Celery beat scheduler
- [x] Health checks on all containers
- [x] Volume persistence for PostgreSQL and Redis
- [x] Flower monitoring (optional profile)
- [x] .env.example with all configuration variables
- [x] Makefile for common commands

### Kubernetes
- [x] Base Kustomize configuration
- [x] Namespace definition
- [x] ConfigMap for environment variables
- [x] Secret template
- [x] PostgreSQL StatefulSet with PVC
- [x] Redis Deployment with PVC
- [x] API Deployment with HorizontalPodAutoscaler (2-10 replicas)
- [x] Worker Deployment with HPA (2-20 replicas)
- [x] Beat Deployment
- [x] Ingress with TLS annotations
- [x] Staging overlay (reduced resources)
- [x] Production overlay (full resources, Multi-AZ)

### CI/CD (GitHub Actions)
- [x] CI/CD pipeline workflow
  - [x] Test job with PostgreSQL and Redis services
  - [x] Linting (flake8, black, mypy)
  - [x] Coverage reporting to Codecov
  - [x] Docker image build and push to GHCR
  - [x] Multi-platform builds (amd64, arm64)
  - [x] Deploy to staging on develop branch
  - [x] Deploy to production on version tags
  - [x] GitHub Release creation
- [x] Security scan workflow
  - [x] Dependency review
  - [x] Trivy vulnerability scanning
  - [x] Docker image scanning
- [x] Dependabot configuration
  - [x] Python dependencies (weekly)
  - [x] Docker images (weekly)
  - [x] GitHub Actions (weekly)

### Infrastructure as Code (Terraform)
- [x] AWS VPC with public/private subnets
- [x] EKS cluster (v1.28) with managed node groups
- [x] RDS PostgreSQL 15
- [x] ElastiCache Redis 7.0
- [x] Security groups
- [x] S3 backend for state
- [x] Staging configuration (staging.tfvars)
- [x] Production configuration (production.tfvars)
- [x] Outputs for kubectl configuration

### Development Tools
- [x] requirements.txt - Production dependencies
- [x] requirements-dev.txt - Development dependencies
- [x] .pre-commit-config.yaml - Git hooks
- [x] .gitignore - Comprehensive ignore rules
- [x] scripts/deploy.sh - Kubernetes deployment script
- [x] scripts/init-db.sql - Database initialization

### Documentation
- [x] README.md - Project overview and quick start
- [x] INFRASTRUCTURE.md - Detailed infrastructure guide
- [x] INFRASTRUCTURE_SUMMARY.md - Deliverables summary
- [x] DEPLOYMENT_CHECKLIST.md - This file

## 📋 Next Steps for Production Deployment

### 1. Configure GitHub Secrets
Navigate to: `https://github.com/builderbuilds123/flight-tracker/settings/secrets/actions`

Required secrets:
```
STAGING_KUBECONFIG        # kubectl config for staging cluster
PRODUCTION_KUBECONFIG     # kubectl config for production cluster
DOCKER_REGISTRY_USERNAME  # Container registry username (if not using GHCR)
DOCKER_REGISTRY_TOKEN     # Container registry token
```

### 2. Update Configuration Files

**Kubernetes Ingress** (`k8s/base/ingress.yaml`):
- Update `api.flighttracker.example.com` to your actual domain
- Configure cert-manager issuer

**Docker Image References** (all k8s/*.yaml):
- Replace `ghcr.io/your-org/` with your actual GitHub organization
- Or update to use your container registry

**Terraform Backend** (`terraform/main.tf`):
- Create S3 bucket for state: `flight-tracker-terraform-state`
- Or update to use a different backend

### 3. Deploy Infrastructure (AWS)

```bash
cd terraform/

# Initialize
terraform init

# Create S3 bucket for state (if using S3 backend)
aws s3 mb s3://flight-tracker-terraform-state

# Plan and apply staging
terraform plan -var-file=staging.tfvars
terraform apply -var-file=staging.tfvars

# Configure kubectl
aws eks update-kubeconfig --name flight-tracker-staging --region us-east-1

# Deploy application
kubectl apply -k ../k8s/overlays/staging/
```

### 4. Verify Deployment

```bash
# Check all pods are running
kubectl get all -n flight-tracker-staging

# Check API health
kubectl port-forward svc/staging-flight-tracker-api 8080:80 -n flight-tracker-staging
curl http://localhost:8080/api/v1/health/ready

# Check logs
kubectl logs -l app=flight-tracker-api -n flight-tracker-staging
```

### 5. Configure Monitoring (Optional)

```bash
# Install Prometheus Stack
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install monitoring prometheus-community/kube-prometheus-stack -n monitoring --create-namespace

# Access Grafana
kubectl port-forward svc/monitoring-grafana -n monitoring 3000:80
```

### 6. Set Up SSL/TLS

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.14.3/cert-manager.yaml

# Create ClusterIssuer for Let's Encrypt
kubectl apply -f k8s/cert-issuer.yaml
```

## 🚀 Quick Commands Reference

### Local Development
```bash
# Start all services
make up

# Run migrations
make migrate

# View logs
make logs

# Run tests
make test
```

### Kubernetes
```bash
# Deploy to staging
make k8s-staging

# Deploy to production
make k8s-prod

# View status
make k8s-status
```

### Terraform
```bash
# Initialize
make tf-init

# Plan staging
make tf-plan-staging

# Apply staging
make tf-apply-staging
```

## 📊 Architecture Summary

```
┌─────────────────────────────────────────────────────┐
│                  Kubernetes Cluster                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │ FastAPI  │  │  Celery  │  │  Celery  │          │
│  │   API    │  │  Worker  │  │   Beat   │          │
│  │ (2-10x)  │  │ (2-20x)  │  │   (1x)   │          │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘          │
│       │             │             │                 │
│       └─────────────┼─────────────┘                 │
│                     │                               │
│       ┌─────────────┼─────────────┐                 │
│       │             │             │                 │
│  ┌────▼────┐  ┌─────▼─────┐       │                 │
│  │PostgreSQL│  │   Redis   │       │                 │
│  │  RDS    │  │ElastiCache│       │                 │
│  │ (HA)    │  │ (Cluster) │       │                 │
│  └─────────┘  └───────────┘       │                 │
└─────────────────────────────────────────────────────┘
```

## 🔒 Security Checklist

- [x] Non-root containers
- [x] Health checks on all services
- [x] Network isolation (private subnets in AWS)
- [ ] Use SealedSecrets or external secret management
- [ ] Enable network policies
- [ ] Configure Pod Security Standards
- [ ] Set up OPA/Gatekeeper policies
- [ ] Enable EKS audit logging
- [ ] Configure CloudWatch alerts

## 📝 Notes

- All infrastructure code is version-controlled in the flight-tracker repository
- CI/CD automatically deploys on push to `develop` (staging) or tags (production)
- Terraform state should be stored in S3 with DynamoDB locking
- Use `terraform plan` before any production changes
- Monitor costs with AWS Cost Explorer
