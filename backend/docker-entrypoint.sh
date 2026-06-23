#!/bin/sh
# ─────────────────────────────────────────────────────────────────────────────
# NeoFace Backend — Docker Entrypoint
# Runs database migrations then starts the Uvicorn server.
# ─────────────────────────────────────────────────────────────────────────────
set -e

# Ensure the app package is discoverable by Python / Alembic
export PYTHONPATH=/app

# Always run from /app so alembic.ini is found and relative paths resolve
cd /app

echo "[entrypoint] Running Alembic migrations..."
alembic upgrade head

echo "[entrypoint] Migrations complete. Starting server..."
# Use WEB_CONCURRENCY set by Render (defaults to 1 on free/standard tier);
# fall back to 1 to avoid memory exhaustion from multiple heavy ML model copies.
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers "${WEB_CONCURRENCY:-1}" \
    --loop uvloop \
    --http httptools \
    --access-log \
    --no-use-colors
