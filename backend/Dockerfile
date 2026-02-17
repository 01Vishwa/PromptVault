# syntax=docker/dockerfile:1
# ── Stage 1: Build ─────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir --prefix=/install .

# ── Stage 2: Runtime ──────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

LABEL maintainer="promptvault-team"
LABEL description="PromptVault Backend"

# Security: run as non-root
RUN apt-get update && apt-get install -y --no-install-recommends curl \
  && rm -rf /var/lib/apt/lists/* \
  && groupadd -r axiom && useradd -r -g axiom axiom

# Install only the pre-built packages
COPY --from=builder /install /usr/local

WORKDIR /app
COPY . .

RUN chown -R axiom:axiom /app
USER axiom

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run with uvicorn – workers configurable via env
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
