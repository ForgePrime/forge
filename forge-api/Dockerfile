FROM python:3.11-slim

WORKDIR /app

# System dependencies for asyncpg and psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies (install first for layer caching)
COPY pyproject.toml .
RUN pip install --no-cache-dir \
    $(python -c "import tomllib; deps=tomllib.load(open('pyproject.toml','rb'))['project']['dependencies']; print(' '.join(deps))")

# Application code
COPY . .

# core/ is mounted via docker-compose volume at /app/core
ENV PYTHONPATH=/app

# Run as non-root user
RUN useradd --create-home --shell /bin/bash forge \
    && mkdir -p /data && chown forge:forge /data
USER forge

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
