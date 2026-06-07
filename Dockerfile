# ── watchlist-monitor web UI — container image for GCP Cloud Run ──────────────
FROM python:3.11-slim

# Faster, cleaner Python in containers
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install deps first for better layer caching
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# App code
COPY monitor/ ./monitor/
COPY webapp/ ./webapp/
COPY config.yaml ./config.yaml

# Cloud Run injects PORT (default 8080). uvicorn must bind 0.0.0.0:$PORT.
ENV PORT=8080
EXPOSE 8080

# Use shell form so $PORT is expanded at runtime.
CMD exec uvicorn webapp.main:app --host 0.0.0.0 --port ${PORT}
