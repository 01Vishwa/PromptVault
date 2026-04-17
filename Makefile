.PHONY: up down up-dev build logs psql migrate test test-unit test-integration run-eval lint format clean

up:
	docker-compose up -d

down:
	docker-compose down

up-dev:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

build:
	docker-compose build

logs:
	docker-compose logs -f

psql:
	docker-compose exec postgres psql -U postgres -d agent_eval

migrate:
	echo "Running alembic migrations (stub)"
	# docker-compose exec eval-core alembic upgrade head

test: test-unit test-integration

test-unit:
	python -m pytest tests/unit

test-integration:
	python -m pytest tests/integration

run-eval:
	echo "Running evaluation (stub)"

lint:
	flake8 .
	mypy .

format:
	black .
	isort .

clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
