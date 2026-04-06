# ── OptiMaintainer: OpenEnv Grading Environment ──
# Optimized python:3.11-slim image, pinned deps, <500MB target

FROM python:3.11-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# ── Install curl for healthcheck + deps (single layer) ──
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/*

# ── Install Python dependencies first (layer caching) ──
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && rm -rf /tmp/* /var/tmp/* /root/.cache

# ── Copy application code ──
COPY __init__.py .
COPY models.py .
COPY graders.py .
COPY scenario_bank.json .
COPY server/ ./server/

# ── Remove unnecessary files to keep image lean ──
RUN find /app -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true \
    && find /usr/local/lib/python3.11 -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# ── Expose port ──
EXPOSE 8000

# ── Health check (required by spec: curl to :8000/health) ──
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# ── Run the server ──
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
