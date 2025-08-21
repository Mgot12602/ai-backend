.PHONY: help install dev worker infra-up infra-down infra-logs test clean

help:
	@echo "Common targets:"
	@echo "  make install     # create venv and install dependencies"
	@echo "  make dev         # start FastAPI with auto-reload (like 'npm run dev')"
	@echo "  make worker      # start Celery worker"
	@echo "  make infra-up    # start MongoDB, Redis, Mongo Express, MinIO"
	@echo "  make infra-down  # stop all infra containers"
	@echo "  make infra-logs  # follow infra logs"
	@echo "  make test        # run pytest"

install:
	python -m venv venv && \
	. venv/bin/activate && \
	pip install --upgrade pip && \
	pip install -r requirements.txt

# Start FastAPI dev server (Swagger at http://localhost:8000/docs)
dev:
	venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Start Celery worker (requires Redis from docker compose)
worker:
	venv/bin/celery -A celery_worker.celery_app worker --loglevel=INFO

infra-up:
	docker compose up -d mongodb redis mongo-express minio

infra-down:
	docker compose down

infra-logs:
	docker compose logs -f mongodb redis mongo-express minio

test:
	venv/bin/pytest -q

clean:
	rm -rf __pycache__ .pytest_cache
