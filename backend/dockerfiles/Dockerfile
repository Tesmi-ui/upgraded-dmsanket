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
COPY dockerfiles/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy single files
COPY main.py .
COPY bulk_processor.py .

# Copy directories (destination must end with /)
COPY api/ api/
COPY models/ models/
COPY core/ core/
COPY engines/ engines/
COPY check_intelligence/ check_intelligence/
COPY validators/ validators/
COPY gender_lib/ gender_lib/
COPY gender_intelligence/ gender_intelligence/
COPY scripts/ scripts/
COPY services/ services/

# Create directories
RUN mkdir -p /app/uploads /app/outputs /app/backups /app/logs \
  /app/data/inbox /app/data/verified /app/data/unverified \
  /app/gender_intelligence_data

# Create non-root user
RUN useradd -m -u 1001 appuser && chown -R appuser:appuser /app
USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

ENV WEB_CONCURRENCY=2
CMD ["gunicorn", "main:app", \
  "--workers", "2", \
  "--worker-class", "uvicorn.workers.UvicornWorker", \
  "--bind", "0.0.0.0:8000", \
  "--timeout", "120", \
  "--access-logfile", "-", \
  "--error-logfile", "-"]