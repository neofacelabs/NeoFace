# ─────────────────────────────────────────────────────────────────────────────
# NeoFace — Makefile
# One-command developer workflow for the entire stack.
#
# Usage:
#   make help       Print all available commands
#   make setup      First-time setup (copy envs, install deps, download models)
#   make start      Start all services (Docker + frontend dev server)
#   make stop       Stop all Docker services
#   make migrate    Run Alembic migrations inside the running API container
#   make test       Run backend test suite
#   make status     Show ONNX model download status
#   make models     Download all ONNX models
#   make logs       Tail the API container logs
#   make clean      Prune dangling Docker resources (safe)
#   make nuke       Full Docker teardown + volume wipe (destructive!)
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: help setup start stop migrate test status models logs clean nuke \
        build lint type-check shell-api shell-db

# ── Colors ─────────────────────────────────────────────────────────────────────
BOLD  := \033[1m
GREEN := \033[0;32m
CYAN  := \033[0;36m
YELLOW:= \033[0;33m
RED   := \033[0;31m
RESET := \033[0m

# ── Default target ─────────────────────────────────────────────────────────────
.DEFAULT_GOAL := help

help: ## Print all available make commands
	@echo ""
	@echo "$(BOLD)NeoFace — Available Commands$(RESET)"
	@echo "────────────────────────────────────────────────────────────"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-18s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(BOLD)Quick Start:$(RESET)"
	@echo "  make setup && make start && make migrate"
	@echo ""

# ── First-time setup ───────────────────────────────────────────────────────────
setup: ## Copy .env files, install frontend deps, download models
	@echo "$(BOLD)$(GREEN)Setting up NeoFace...$(RESET)"

	@# Backend .env
	@if [ ! -f backend/.env ]; then \
		cp backend/.env.example backend/.env; \
		echo "  ✅ Created backend/.env (edit it with your credentials)"; \
	else \
		echo "  ⏭  backend/.env already exists — skipping"; \
	fi

	@# Frontend .env.local
	@if [ ! -f frontend/.env.local ]; then \
		cp frontend/.env.example frontend/.env.local; \
		echo "  ✅ Created frontend/.env.local (set NEXT_PUBLIC_API_BASE_URL)"; \
	else \
		echo "  ⏭  frontend/.env.local already exists — skipping"; \
	fi

	@# Frontend npm install
	@echo "  📦 Installing frontend dependencies..."
	@cd frontend && npm install --prefer-offline --silent
	@echo "  ✅ Frontend dependencies installed"

	@# Models
	@echo "  🧠 Checking ONNX model status..."
	@cd backend && python3 scripts/download_models.py --status

	@echo ""
	@echo "$(BOLD)$(GREEN)Setup complete!$(RESET)"
	@echo "  Next: $(CYAN)make start$(RESET)  →  then  $(CYAN)make migrate$(RESET)"
	@echo ""

# ── Download models ────────────────────────────────────────────────────────────
models: ## Download all ONNX model weights (~770 MB, skips existing)
	@echo "$(BOLD)$(CYAN)Downloading ONNX models...$(RESET)"
	@echo "  Note: dpt_hybrid.onnx is ~508 MB and may take several minutes."
	cd backend && python3 scripts/download_models.py --all

status: ## Show ONNX model download status
	cd backend && python3 scripts/download_models.py --status

# ── Start / Stop ───────────────────────────────────────────────────────────────
start: ## Start full stack (Docker backend + Next.js frontend)
	@chmod +x start.sh cleanup.sh
	./start.sh

stop: ## Stop all Docker services (preserves volumes)
	docker compose stop
	@echo "$(GREEN)  ✅ All services stopped$(RESET)"

build: ## Force rebuild Docker image (use after changing Dockerfile/requirements)
	DOCKER_BUILDKIT=1 docker compose build --no-cache api worker beat

# ── Database ───────────────────────────────────────────────────────────────────
migrate: ## Run Alembic migrations (requires running API container)
	@echo "$(BOLD)Running database migrations...$(RESET)"
	docker compose exec api alembic upgrade head
	@echo "$(GREEN)  ✅ Migrations complete$(RESET)"

migrate-status: ## Show current Alembic migration status
	docker compose exec api alembic current

migrate-history: ## Show full Alembic migration history
	docker compose exec api alembic history --verbose

migrate-down: ## Rollback one migration step
	docker compose exec api alembic downgrade -1

# ── Testing ────────────────────────────────────────────────────────────────────
test: ## Run backend test suite
	@echo "$(BOLD)Running backend tests...$(RESET)"
	cd backend && python -m pytest app/tests/ -v --tb=short

test-cov: ## Run tests with coverage report
	cd backend && python -m pytest app/tests/ -v --cov=app --cov-report=term-missing

test-fast: ## Run tests excluding slow integration tests
	cd backend && python -m pytest app/tests/ -v --tb=short -m "not slow"

# ── Code Quality ───────────────────────────────────────────────────────────────
lint: ## Run ruff linter on backend
	cd backend && ruff check app/

format: ## Auto-format backend code with ruff
	cd backend && ruff format app/

type-check: ## Run mypy type checker on backend
	cd backend && mypy app/ --ignore-missing-imports

frontend-lint: ## Run ESLint on frontend
	cd frontend && npm run lint

frontend-type-check: ## Run TypeScript type checker on frontend
	cd frontend && npm run type-check

# ── Logs ───────────────────────────────────────────────────────────────────────
logs: ## Tail API container logs (Ctrl+C to stop)
	docker compose logs -f api

logs-all: ## Tail all container logs
	docker compose logs -f

logs-worker: ## Tail Celery worker logs
	docker compose logs -f worker

# ── Shell Access ───────────────────────────────────────────────────────────────
shell-api: ## Open a shell inside the running API container
	docker compose exec api bash

shell-db: ## Open psql shell in the Postgres container
	docker compose exec postgres psql -U neoface -d neoface_db

# ── Cleanup ────────────────────────────────────────────────────────────────────
clean: ## Safe prune — remove dangling images, stopped containers, unused networks
	@echo "$(BOLD)$(YELLOW)Pruning unused Docker resources...$(RESET)"
	@chmod +x cleanup.sh && ./cleanup.sh
	@echo "$(GREEN)  ✅ Cleanup complete$(RESET)"

nuke: ## ⚠️  DESTRUCTIVE: tear down all containers AND volumes (wipes local DB)
	@echo "$(BOLD)$(RED)⚠️  This will DELETE all local database data!$(RESET)"
	@read -p "Type 'yes' to confirm: " confirm && [ "$$confirm" = "yes" ] || exit 1
	docker compose down --volumes --remove-orphans
	docker image prune -f
	@echo "$(GREEN)  ✅ Full teardown complete$(RESET)"

# ── Docker compose shortcuts ───────────────────────────────────────────────────
ps: ## Show running containers and their status
	docker compose ps

health: ## Check health of all containers
	@echo "$(BOLD)Container health:$(RESET)"
	@docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

restart-api: ## Restart only the API container (preserves DB)
	docker compose restart api
	@echo "$(GREEN)  ✅ API restarted$(RESET)"
