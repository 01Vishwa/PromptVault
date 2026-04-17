FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install --no-cache-dir \
    fastapi uvicorn[standard] httpx pydantic pydantic-settings \
    python-jose[cryptography]

EXPOSE 8080

CMD ["uvicorn", "services.gateway.main:app", \
     "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]
