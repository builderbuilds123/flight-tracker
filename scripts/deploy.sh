#!/bin/bash
# Flight Tracker Deployment Script
# Usage: ./scripts/deploy.sh [staging|production]

set -e

ENVIRONMENT=${1:-staging}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "Flight Tracker Deployment"
echo "Environment: $ENVIRONMENT"
echo "=========================================="

# Validate environment
if [[ "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "production" ]]; then
    echo "Error: Environment must be 'staging' or 'production'"
    exit 1
fi

# Check prerequisites
command -v kubectl >/dev/null 2>&1 || { echo "kubectl is required but not installed."; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "docker is required but not installed."; exit 1; }

cd "$PROJECT_ROOT"

# Build and push Docker images
echo ""
echo "Building Docker images..."
docker build -t flight-tracker-api:$ENVIRONMENT -f Dockerfile .
docker build -t flight-tracker-worker:$ENVIRONMENT -f Dockerfile.worker .
docker build -t flight-tracker-beat:$ENVIRONMENT -f Dockerfile.beat .

# Tag for registry (update with your registry)
REGISTRY=${DOCKER_REGISTRY:-ghcr.io/your-org}
echo ""
echo "Tagging images for registry: $REGISTRY"
docker tag flight-tracker-api:$ENVIRONMENT $REGISTRY/flight-tracker-api:$ENVIRONMENT
docker tag flight-tracker-worker:$ENVIRONMENT $REGISTRY/flight-tracker-worker:$ENVIRONMENT
docker tag flight-tracker-beat:$ENVIRONMENT $REGISTRY/flight-tracker-beat:$ENVIRONMENT

# Push to registry
echo ""
echo "Pushing images to registry..."
docker push $REGISTRY/flight-tracker-api:$ENVIRONMENT
docker push $REGISTRY/flight-tracker-worker:$ENVIRONMENT
docker push $REGISTRY/flight-tracker-beat:$ENVIRONMENT

# Deploy to Kubernetes
echo ""
echo "Deploying to Kubernetes..."
if [[ "$ENVIRONMENT" == "staging" ]]; then
    kubectl apply -k k8s/overlays/staging/
else
    kubectl apply -k k8s/overlays/production/
fi

# Wait for deployment
echo ""
echo "Waiting for deployment to complete..."
kubectl rollout status deployment/$(if [[ "$ENVIRONMENT" == "staging" ]]; then echo "staging-"; else echo "prod-"; fi)flight-tracker-api -n flight-tracker-$ENVIRONMENT

# Show status
echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "Checking service status..."
kubectl get all -n flight-tracker-$ENVIRONMENT

echo ""
echo "API Endpoint:"
if [[ "$ENVIRONMENT" == "staging" ]]; then
    echo "  https://staging-api.flighttracker.example.com"
else
    echo "  https://api.flighttracker.example.com"
fi

echo ""
echo "Health Check:"
echo "  curl https://$(if [[ "$ENVIRONMENT" == "staging" ]]; then echo "staging-"; fi)api.flighttracker.example.com/api/v1/health/ready"
