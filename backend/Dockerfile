# ─────────────────────────────────────────────────────────────────────────────
# NeoFace Backend — Production Dockerfile
# Multi-stage build:
#   Stage 1 (builder): Install Python deps with uv
#   Stage 2 (runtime): Minimal image with only runtime artifacts
# ─────────────────────────────────────────────────────────────────────────────

# ── Stage 1: Builder ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

# System dependencies for OpenCV, InsightFace, and mediapipe
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    cmake \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgl1 \
    libglib2.0-dev \
    libprotobuf-dev \
    protobuf-compiler \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /build

# Copy dependency files first (layer caching)
COPY requirements.txt ./

# Install dependencies into a virtual environment
RUN uv venv /opt/venv --python python3.12
ENV PATH="/opt/venv/bin:$PATH"
RUN uv pip install --no-cache -r requirements.txt


# ── Stage 2: Runtime ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Labels
LABEL maintainer="NeoFace Engineering <engineering@neoface.io>"
LABEL version="1.0.0"
LABEL description="NeoFace Biometric Authentication Engine"

# Runtime system deps (shared libs only — no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    libgl1 \
    libprotobuf-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for security
RUN groupadd -r neoface && useradd -r -g neoface -s /bin/false neoface

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code and migration files
COPY --chown=neoface:neoface ./app ./app
COPY --chown=neoface:neoface ./migrations ./migrations
COPY --chown=neoface:neoface ./alembic.ini ./alembic.ini
COPY --chown=neoface:neoface .env.example .env.example

# Startup entrypoint script (runs migrations then starts server)
COPY --chown=neoface:neoface ./docker-entrypoint.sh ./docker-entrypoint.sh
RUN chmod +x ./docker-entrypoint.sh

# Create directories for storage and logs
RUN mkdir -p /app/storage/faces /app/logs /app/.insightface /app/models \
    && chown -R neoface:neoface /app/storage /app/logs /app/.insightface /app/models

# InsightFace model cache directory
ENV INSIGHTFACE_HOME=/app/.insightface

# Python settings
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Switch to non-root user
USER neoface

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Entrypoint: run migrations then start server
ENTRYPOINT ["/app/docker-entrypoint.sh"]
