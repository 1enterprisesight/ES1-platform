# ES1 Platform Makefile
# Common commands for development and deployment

.PHONY: help up down logs build build-all build-multiarch deploy-local setup clean new-service test lint

REGISTRY ?= ghcr.io/1enterprisesight/es1-platform
TAG ?= local

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# =============================================================================
# Docker Compose Commands
# =============================================================================

up: ## Start all services with Docker Compose (hot reload)
	docker compose up -d

up-infra: ## Start only infrastructure (Postgres + Redis)
	docker compose -f docker-compose.infra.yml up -d

down: ## Stop all Docker Compose services
	docker compose down
	docker compose -f docker-compose.infra.yml down 2>/dev/null || true

logs: ## Tail logs from all services
	docker compose logs -f

logs-gw: ## Tail logs from KrakenD only
	docker compose logs -f krakend

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
	kubectl get pods -n es1-platform
	kubectl get pods -n es1-infrastructure
	@echo ""
	@echo "=== Services ==="
	kubectl get svc -n es1-platform
	kubectl get svc -n es1-infrastructure

port-forward: ## Port forward KrakenD to localhost:8080
	kubectl port-forward svc/krakend 8080:80 -n es1-platform

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
