# Forge Platform — production image (starter template, tune before deploy)
#
# Multi-stage build:
#   builder  — installs deps into a virtualenv
#   runtime  — thin image with just the venv + app code, non-root user
#
# Build:
#   docker build -t forge-platform:latest -f platform/Dockerfile platform/
#
# Run (sanity):
#   docker run --rm -p 8000:8000 \
#     -e FORGE_DATABASE_URL=postgresql://... \
#     -e FORGE_JWT_SECRET=$(openssl rand -hex 32) \
#     forge-platform:latest

# ---------- Builder ----------
FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

# System deps for psycopg2 + build tooling
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install deps only (without the app itself) for better cache layering
RUN pip install --upgrade pip && \
    pip install .

# ---------- Runtime ----------
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    FORGE_HOST=0.0.0.0 \
    FORGE_PORT=8000 \
    FORGE_LOG_JSON=true

# Minimal runtime deps for psycopg2 + curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user — reduces blast radius if app is compromised
RUN useradd --create-home --shell /bin/bash --uid 1001 forge

COPY --from=builder --chown=forge:forge /opt/venv /opt/venv
WORKDIR /app
COPY --chown=forge:forge app/ ./app/
COPY --chown=forge:forge pyproject.toml ./

USER forge

EXPOSE 8000

# Liveness probe — matches SLO-1. `/ready` (used by readiness) is a
# separate endpoint; orchestrators should point readiness at /ready.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Single-worker default; production should override via CMD ["uvicorn",
# "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
# or run behind gunicorn with uvicorn workers.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
