# Flight Tracker - Makefile
# Common development and deployment commands

.PHONY: help install dev test build up down logs clean migrate

# ===========================================
# Help
# ===========================================
help:
	@echo "Flight Tracker - Available Commands"
	@echo ""
	@echo "Development:"
	@echo "  install     Install Python dependencies"
	@echo "  dev         Run development server"
	@echo "  test        Run tests"
	@echo "  lint        Run linters"
	@echo "  format      Format code with black"
	@echo ""
	@echo "Docker:"
	@echo "  up          Start all services"
	@echo "  down        Stop all services"
	@echo "  build       Build Docker images"
	@echo "  logs        View logs"
	@echo "  shell       Open shell in API container"
	@echo ""
	@echo "Database:"
	@echo "  migrate     Run database migrations"
	@echo "  db-shell    Open PostgreSQL shell"
	@echo ""
	@echo "Kubernetes:"
	@echo "  k8s-staging Deploy to staging"
	@echo "  k8s-prod    Deploy to production"
	@echo "  k8s-delete  Delete from Kubernetes"
	@echo ""
	@echo "Terraform:"
	@echo "  tf-init     Initialize Terraform"
	@echo "  tf-plan     Plan infrastructure"
	@echo "  tf-apply    Apply infrastructure"
	@echo "  tf-destroy  Destroy infrastructure"

# ===========================================
# Development
# ===========================================
install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt 2>/dev/null || true

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v --cov=app --cov-report=term-missing

lint:
	flake8 app tests
	black --check app tests
	mypy app --ignore-missing-imports

format:
	black app tests
	isort app tests

# ===========================================
# Docker Compose
# ===========================================
up:
	docker-compose up -d

up-monitoring:
	docker-compose --profile monitoring up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

build:
	docker-compose build

shell:
	docker-compose exec api /bin/bash

db-shell:
	docker-compose exec postgres psql -U flighttracker -d flight_tracker

migrate:
	docker-compose exec api python -c "from app.core.database import init_db; import asyncio; asyncio.run(init_db())"

clean:
	docker-compose down -v
	docker-compose rm -f

# ===========================================
# Kubernetes
# ===========================================
k8s-staging:
	kubectl apply -k k8s/overlays/staging/

k8s-prod:
	kubectl apply -k k8s/overlays/production/

k8s-delete:
	kubectl delete -k k8s/overlays/staging/ --ignore-not-found
	kubectl delete -k k8s/overlays/production/ --ignore-not-found

k8s-status:
	kubectl get all -n flight-tracker-staging
	kubectl get all -n flight-tracker-production

# ===========================================
# Terraform
# ===========================================
tf-init:
	cd terraform && terraform init

tf-plan-staging:
	cd terraform && terraform plan -var-file=staging.tfvars

tf-plan-prod:
	cd terraform && terraform plan -var-file=production.tfvars

tf-apply-staging:
	cd terraform && terraform apply -var-file=staging.tfvars

tf-apply-prod:
	cd terraform && terraform apply -var-file=production.tfvars

tf-destroy:
	cd terraform && terraform destroy

tf-output:
	cd terraform && terraform output

# ===========================================
# CI/CD
# ===========================================
ci-test:
	docker-compose -f docker-compose.ci.yml up --abort-on-container-exit

release:
	@echo "Creating release..."
	git tag -a $(version) -m "Release $(version)"
	git push origin $(version)
