# Fivefold backend — FastAPI + scoring engine.
# Build context is the repo root so we can bundle data/ alongside backend/:
#     docker build -f backend/Dockerfile -t fivefold-backend .
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install deps first for better layer caching.
COPY backend/pyproject.toml ./backend/pyproject.toml
RUN pip install "pydantic>=2.6" "fastapi>=0.110" "uvicorn[standard]>=0.29"

# Source + data.
COPY backend/fivefold ./backend/fivefold
COPY data ./data

WORKDIR /app/backend

ENV FIVEFOLD_CORS_ORIGINS=""
EXPOSE 8000

CMD ["uvicorn", "fivefold.api:app", "--host", "0.0.0.0", "--port", "8000"]
