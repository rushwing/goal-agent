# syntax=docker/dockerfile:1
# Multi-stage build for the Vacation Study Planner API.
#
# Stage 1 – builder: install deps with uv into /app/.venv
# Stage 2 – runtime: copy only the venv + app source, no build tools
#
# Build:  docker build -t vocation-planner .
# Run:    docker compose up   (see docker-compose.yml)

# ── Stage 1: builder ────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /build

# Copy dependency manifests first (layer-cache friendly)
COPY pyproject.toml .python-version ./

# Install runtime dependencies into a local .venv (no system-site)
RUN uv sync --no-dev --no-editable

# ── Stage 2: runtime ────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Non-root user for security
RUN useradd --create-home --shell /bin/bash planner
WORKDIR /app

# Copy the pre-built virtualenv from builder
COPY --from=builder /build/.venv /app/.venv

# Copy application source
COPY app/        ./app/
COPY alembic/    ./alembic/
COPY alembic.ini ./

# Make venv the default Python
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Drop to non-root
USER planner

EXPOSE 8000

# Single worker – APScheduler runs in-process
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--loop", "uvloop"]
