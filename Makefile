# Platform Makefile
# Common commands for development and deployment

.PHONY: help up up-infra up-full up-airflow up-langfuse up-langflow up-gateway-manager up-platform-manager up-ml-stack up-aiml up-monitoring down logs logs-gw logs-airflow logs-gateway-manager logs-platform-manager logs-aiml logs-monitoring build build-all build-multiarch deploy-local setup clean new-service test lint ctx-local ctx-show status port-forward undeploy deploy-infra build-push generate-creds

REGISTRY ?= ghcr.io/1enterprisesight/es1-platform
TAG ?= local

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# =============================================================================
# Docker Compose Commands
# =============================================================================

up: ## Start base services (Postgres, Redis, KrakenD)
	docker compose up -d

up-infra: ## Start only infrastructure (Postgres + Redis)
	docker compose -f docker-compose.infra.yml up -d

up-full: ## Start ALL services (infrastructure + Airflow + Langfuse + Langflow + AI/ML + Platform Manager)
	docker compose \
		-f docker-compose.yml \
		-f docker-compose.airflow.yml \
		-f docker-compose.langfuse.yml \
		-f docker-compose.langflow.yml \
		-f docker-compose.aiml.yml \
		-f docker-compose.es1-platform-manager.yml \
		up -d

up-airflow: ## Start base + Airflow
	docker compose -f docker-compose.yml -f docker-compose.airflow.yml up -d

up-langfuse: ## Start base + Langfuse
	docker compose -f docker-compose.yml -f docker-compose.langfuse.yml up -d

up-langflow: ## Start base + Langflow
	docker compose -f docker-compose.yml -f docker-compose.langflow.yml up -d

up-gateway-manager: ## Start base + Gateway Manager (legacy)
	docker compose -f docker-compose.yml -f docker-compose.gateway-manager.yml up -d

up-platform-manager: ## Start base + Platform Manager
	docker compose -f docker-compose.yml -f docker-compose.es1-platform-manager.yml up -d

up-ml-stack: ## Start Airflow + Langfuse + Langflow (ML/AI stack)
	docker compose \
		-f docker-compose.yml \
		-f docker-compose.airflow.yml \
		-f docker-compose.langfuse.yml \
		-f docker-compose.langflow.yml \
		up -d

up-aiml: ## Start base + AI/ML stack (Ollama, MLflow, pgvector DB)
	docker compose -f docker-compose.yml -f docker-compose.aiml.yml up -d

up-aiml-full: ## Start AI/ML stack with Platform Manager
	docker compose \
		-f docker-compose.yml \
		-f docker-compose.aiml.yml \
		-f docker-compose.es1-platform-manager.yml \
		up -d

up-monitoring: ## Start base + Monitoring (Prometheus, Grafana)
	docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d

up-full-monitoring: ## Start ALL services + Monitoring
	docker compose \
		-f docker-compose.yml \
		-f docker-compose.airflow.yml \
		-f docker-compose.langfuse.yml \
		-f docker-compose.langflow.yml \
		-f docker-compose.aiml.yml \
		-f docker-compose.es1-platform-manager.yml \
		-f docker-compose.monitoring.yml \
		up -d

down: ## Stop all Docker Compose services
	docker compose \
		-f docker-compose.yml \
		-f docker-compose.airflow.yml \
		-f docker-compose.langfuse.yml \
		-f docker-compose.langflow.yml \
		-f docker-compose.gateway-manager.yml \
		-f docker-compose.es1-platform-manager.yml \
		-f docker-compose.aiml.yml \
		-f docker-compose.monitoring.yml \
		down 2>/dev/null || true
	docker compose -f docker-compose.infra.yml down 2>/dev/null || true

logs: ## Tail logs from all services
	docker compose logs -f

logs-gw: ## Tail logs from KrakenD only
	docker compose logs -f krakend

logs-airflow: ## Tail logs from Airflow services
	docker compose -f docker-compose.yml -f docker-compose.airflow.yml logs -f airflow-webserver airflow-scheduler airflow-worker

logs-gateway-manager: ## Tail logs from Gateway Manager (legacy)
	docker compose -f docker-compose.yml -f docker-compose.gateway-manager.yml logs -f gateway-manager-api gateway-manager-ui

logs-platform-manager: ## Tail logs from Platform Manager
	docker compose -f docker-compose.yml -f docker-compose.es1-platform-manager.yml logs -f es1-platform-manager-api es1-platform-manager-ui

logs-aiml: ## Tail logs from AI/ML stack
	docker compose -f docker-compose.yml -f docker-compose.aiml.yml logs -f aiml-postgres ollama ollama-webui mlflow

logs-monitoring: ## Tail logs from Monitoring stack
	docker compose -f docker-compose.yml -f docker-compose.monitoring.yml logs -f prometheus grafana

# =============================================================================
# Build Commands
# =============================================================================

build: ## Build KrakenD image
	docker build -t $(REGISTRY)/krakend:$(TAG) -f services/krakend/Dockerfile services/krakend

build-all: ## Build all service images
	./scripts/build-all.sh $(TAG)

build-multiarch: ## Build multi-arch images (amd64 + arm64)
	./scripts/build-multiarch.sh $(TAG)

build-push: ## Build and push multi-arch images to registry
	PUSH=true ./scripts/build-multiarch.sh $(TAG)

# =============================================================================
# Kubernetes Commands
# =============================================================================

setup: ## One-time local environment setup
	./scripts/setup-local.sh

deploy-local: ## Deploy to local Kubernetes
	./scripts/deploy-local.sh

deploy-infra: ## Deploy only infrastructure to local K8s
	kubectl apply -f k8s/base/namespaces/namespaces.yaml
	kubectl apply -f k8s/overlays/local/secrets.yaml
	kubectl apply -f k8s/base/infrastructure/

undeploy: ## Remove all from local Kubernetes
	kubectl delete -k k8s/overlays/local --ignore-not-found

status: ## Show Kubernetes status
	@echo "=== Pods ==="
	kubectl get pods -n engine-platform
	kubectl get pods -n engine-infrastructure
	@echo ""
	@echo "=== Services ==="
	kubectl get svc -n engine-platform
	kubectl get svc -n engine-infrastructure

port-forward: ## Port forward KrakenD to localhost:8080
	kubectl port-forward svc/krakend 8080:80 -n engine-platform

# =============================================================================
# Credential Generation
# =============================================================================

generate-creds: ## Generate production credentials (.env format)
	@./scripts/generate-credentials.sh

generate-creds-k8s: ## Generate production credentials (K8s secrets YAML)
	@./scripts/generate-credentials.sh --format=k8s-secrets

# =============================================================================
# Upgrade Commands
# =============================================================================

upgrade: ## Upgrade all services (pull images, migrate DB, restart)
	./scripts/upgrade.sh

upgrade-dry-run: ## Show what upgrade would do (no changes)
	./scripts/upgrade.sh --dry-run

# =============================================================================
# Development Commands
# =============================================================================

new-service: ## Create a new service (usage: make new-service NAME=my-service TYPE=python)
	@if [ -z "$(NAME)" ] || [ -z "$(TYPE)" ]; then \
		echo "Usage: make new-service NAME=my-service TYPE=python|node|go"; \
		exit 1; \
	fi
	./scripts/new-service.sh $(NAME) $(TYPE)

test: ## Run tests for all services
	@echo "No tests configured yet"

lint: ## Lint all services
	@echo "No linting configured yet"

# =============================================================================
# Cleanup Commands
# =============================================================================

clean: ## Clean up Docker resources
	docker compose down -v --remove-orphans
	docker system prune -f

clean-all: ## Clean up everything including images
	docker compose down -v --remove-orphans
	docker system prune -af
	docker volume prune -f

# =============================================================================
# Context Management
# =============================================================================

ctx-local: ## Switch kubectl to docker-desktop context
	kubectl config use-context docker-desktop

ctx-show: ## Show current kubectl context
	kubectl config current-context
