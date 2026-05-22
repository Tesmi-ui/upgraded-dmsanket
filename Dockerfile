# ============================================================================
# BRLF Backend Dockerfile (Production) — v5.0
# ============================================================================
FROM python:3.11-slim

LABEL version="5.0.0" \
  description="BRLF-Sanket Data Migration API"

RUN apt-get update && apt-get install -y --no-install-recommends \
  gcc libpq-dev curl \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies
COPY backend/dockerfiles/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy single files
COPY backend/main.py .
COPY backend/bulk_processor.py .

# Copy directories (destination must end with /)
COPY backend/api/ api/
COPY backend/models/ models/
COPY backend/core/ core/
COPY backend/engines/ engines/
COPY backend/check_intelligence/ check_intelligence/
COPY backend/validators/ validators/
COPY backend/gender_lib/ gender_lib/
COPY backend/gender_intelligence/ gender_intelligence/
COPY backend/scripts/ scripts/
COPY backend/services/ services/

# Create directories
RUN mkdir -p /app/uploads /app/outputs /app/backups /app/logs \
  /app/data/inbox /app/data/verified /app/data/unverified \
  /app/gender_intelligence_data

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:7860/health || exit 1

EXPOSE 7860

ENV WEB_CONCURRENCY=2
CMD ["gunicorn", "main:app", \
  "--workers", "2", \
  "--worker-class", "uvicorn.workers.UvicornWorker", \
  "--bind", "0.0.0.0:7860", \
  "--timeout", "120", \
  "--access-logfile", "-", \
  "--error-logfile", "-"]
