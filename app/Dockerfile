# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1: build the React frontend (frontend/dist is what routes_pages.py
# and the /assets mount in main.py serve — see frontend/README dev notes).
# ---------------------------------------------------------------------------
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2: Python backend runtime, serving the built frontend as static files.
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS runtime
WORKDIR /app

COPY requirements.txt ./
# build-essential is only needed to compile a couple of chromadb's transitive
# C-extension deps when no prebuilt wheel exists for this platform/Python
# combo — installed and removed in one layer so it doesn't inflate the image.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y build-essential \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY backend/ ./backend/
COPY scripts/ ./scripts/
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# /app/data holds the SQLite DB, the ChromaDB persist dir, and uploaded
# report files — everything this app needs to survive a container restart.
# Mount a volume there (docker-compose.yml does this for local/EC2 use).
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app
USER appuser

ENV DATABASE_PATH=/app/data/cis.db \
    CHROMA_PERSIST_DIR=/app/data/chroma_db \
    UPLOAD_DIR=/app/data/uploads \
    PYTHONUNBUFFERED=1

EXPOSE 8000
VOLUME ["/app/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Single worker, intentionally: SQLite is single-writer, so running multiple
# uvicorn worker processes against the same DB file risks "database is
# locked" errors under concurrent writes. Scale this app vertically (a
# bigger instance), not horizontally across workers or containers — see
# docs/architecture.pdf and README's Known limitations for the same
# constraint applied to appointment booking's conflict checks.
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
