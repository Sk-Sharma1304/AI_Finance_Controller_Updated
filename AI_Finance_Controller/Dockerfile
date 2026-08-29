# AI Finance Controller — API backend
#
# Build:  docker build -t finance-controller-api .
# Run:    docker run -p 8000:8000 --env-file .env finance-controller-api
#
# The trained model artifacts in ml/models/ are baked into the
# image so it serves real (not fallback-fit) predictions on first
# boot. Retrain and rebuild the image to ship a new model version
# rather than mounting models in at runtime -- keeps "what's
# running" and "what's in the image" the same thing, which matters
# for the audit trail's model_version field.

FROM python:3.12-slim AS base

# Runs as a non-root user; only default python:slim ships as root.
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Install dependencies first so this layer is cached across code
# changes that don't touch requirements.txt.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Application code (see .dockerignore for what's excluded).
COPY . .

# SQLite file (if DATABASE_URL isn't overridden to point at
# Postgres) needs a writable directory owned by the app user.
RUN mkdir -p /app/data_store && chown -R appuser:appuser /app

USER appuser

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DATABASE_URL=sqlite:////app/data_store/finance_controller.db

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
