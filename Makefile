.PHONY: help install env-print api dev worker infra-core-up infra-core-logs infra-all-up infra-up infra-down infra-logs test clean

# Use bash for better scriptability
SHELL := /bin/bash

# Reusable macros
# Loads .env if present so variables are available to the command that follows
ENV = set -a; [ -f .env ] && . ./.env; set +a

# Prefer python3 if available; fallback to python
PYTHON ?= $(shell command -v python3 >/dev/null 2>&1 && echo python3 || echo python)

# Common commands (with sensible defaults if vars are missing)
API_CMD = venv/bin/uvicorn main:app --host "$${API_HOST:-0.0.0.0}" --port "$${API_PORT:-8000}" --reload --log-level debug
WORKER_CMD = venv/bin/celery -A celery_worker.celery_app worker -Q "$${CELERY_QUEUE_NAME:-ai_jobs}" --loglevel=INFO

help:
	@echo "Common targets:"
	@echo "  make install     # create venv and install dependencies"
	@echo "  make env-print   # show key env vars from .env"
	@echo "  make api         # start FastAPI only (auto-reload)"
	@echo "  make worker      # start Celery worker only (local)"
	@echo "  make dev         # start FastAPI + local Celery worker (auto-reload)"
	@echo "  make infra-core-up    # start MongoDB + Redis"
	@echo "  make infra-core-logs  # follow core infra logs"
	@echo "  make infra-all-up     # start all compose services (incl. api/worker)"
	@echo "  make infra-up         # alias of infra-all-up"
	@echo "  make infra-down  # stop all infra containers"
	@echo "  make infra-logs  # follow infra logs"
	@echo "  make test        # run pytest"

install:
	$(PYTHON) -m venv venv && \
	venv/bin/python -m pip install --upgrade pip && \
	venv/bin/pip install -r requirements-api.txt -r requirements-worker.txt

# Print important env values for sanity checking
env-print:
	$(ENV) ; \
	printf "API_HOST=%s\nAPI_PORT=%s\nCELERY_QUEUE_NAME=%s\nMONGODB_URL=%s\nREDIS_URL=%s\n" \
	"$${API_HOST}" "$${API_PORT}" "$${CELERY_QUEUE_NAME}" "$${MONGODB_URL}" "$${REDIS_URL}"

# Start only the FastAPI dev server (Swagger at http://localhost:8000/docs)
api:
	$(ENV) ; $(API_CMD)

# Start FastAPI dev server + local Celery worker (Swagger at http://localhost:8000/docs)
dev:
	$(ENV) ; \
	( $(API_CMD) & ); \
	( $(WORKER_CMD) & ); \
	wait

# Start Celery worker (requires Redis from docker compose)
worker:
	$(ENV) ; $(WORKER_CMD)

# Core infra (MongoDB + Redis) for local dev
infra-core-up:
	docker compose up -d mongodb redis

infra-core-logs:
	docker compose logs -f mongodb redis

# All services (including containerized api/worker)
infra-all-up:
	docker compose up -d mongodb redis mongo-express minio celery-worker api

# Backwards compatible aliases
infra-up: infra-all-up

infra-down:
	docker compose down

infra-logs:
	docker compose logs -f mongodb redis mongo-express minio celery-worker api

test:
	venv/bin/pytest -q

clean:
	rm -rf __pycache__ .pytest_cache
