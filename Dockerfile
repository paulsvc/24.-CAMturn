# LatheCAM Production Multi-Stage Dockerfile
# Builds React+Three.js frontend and packages headless Python CAD/CAM backend

# ==============================================================================
# Stage 1: Build Frontend Assets (React + Vite + TypeScript)
# ==============================================================================
FROM node:22-alpine AS frontend-builder
WORKDIR /build

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# ==============================================================================
# Stage 2: Headless Python Backend with OpenCASCADE & Geometry Stack
# ==============================================================================
FROM python:3.11-slim-bookworm AS production

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=8000

# Install minimal OS runtime dependencies for OpenCASCADE and headless libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgomp1 \
    libxrender1 \
    libxext6 \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt requirements-core.txt ./
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements-core.txt && \
    pip install --no-cache-dir fastapi uvicorn[standard] python-multipart httpx

# Copy Backend Source Code
COPY src/ /app/src/
ENV PYTHONPATH="/app/src"

# Copy Compiled Frontend Assets from Stage 1 into Web Static Directory
COPY --from=frontend-builder /build/dist /app/static

# Create non-privileged user for security
RUN useradd -m -u 1000 latheuser && \
    mkdir -p /app/data /app/uploads && \
    chown -R latheuser:latheuser /app

USER latheuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "lathecam_web.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
