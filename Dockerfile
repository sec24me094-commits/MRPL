# syntax=docker/dockerfile:1
FROM python:3.10-slim

# Set environment variables for Python runtime optimization & security
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Update base system packages and install minimal runtime utilities
RUN apt-get update && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
        curl \
        poppler-utils \
        tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Create a dedicated non-privileged user and group for application execution
RUN groupadd --gid 10001 appgroup \
    && useradd --uid 10001 --gid appgroup --shell /bin/false --no-create-home appuser

# Set the secure working directory
WORKDIR /app

# Copy dependency manifests first to leverage Docker build layer caching
COPY requirements.txt .

# Install pinned Python dependencies without caching wheels
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code into the container with non-root ownership
COPY --chown=appuser:appgroup . /app

# Drop privileges to non-root user
USER appuser

# Expose the application service port
EXPOSE 8000

# Health check to ensure service vitality
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Launch the FastAPI service via Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
