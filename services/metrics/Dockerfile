FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install --no-cache-dir \
    fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg \
    pydantic pydantic-settings redis

EXPOSE 8002

CMD ["uvicorn", "services.metrics.presentation.api.main:app", \
     "--host", "0.0.0.0", "--port", "8002", "--workers", "2"]
