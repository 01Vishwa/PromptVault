FROM python:3.11-slim

WORKDIR /app

# Install system deps for asyncpg + anthropic
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[prod]" 2>/dev/null || \
    pip install --no-cache-dir \
        fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg \
        pydantic pydantic-settings httpx anthropic opentelemetry-sdk \
        opentelemetry-exporter-otlp-proto-grpc langchain langchain-anthropic \
        celery redis sse-starlette python-jose[cryptography] alembic

COPY . .

EXPOSE 8000

CMD ["uvicorn", "services.agent_eval.presentation.api.main:app", \
     "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
