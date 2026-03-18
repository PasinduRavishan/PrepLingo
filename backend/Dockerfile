# Multi-stage build: download model at build time, zero cold-start overhead
FROM python:3.11-slim as builder

WORKDIR /app
COPY requirements.txt .

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the embedding model (~430 MB) into the image
# This runs once at build time, so the container starts with zero embedding API latency
RUN python -c "from langchain_huggingface import HuggingFaceEmbeddings; \
               model = HuggingFaceEmbeddings(model_name='BAAI/bge-base-en-v1.5'); \
               print('✅ Embedding model pre-downloaded and cached')"

# Final stage: runtime image with all dependencies + cached model
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /root/.cache /root/.cache

# Copy app code
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY .env* ./

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)"

# Expose port
EXPOSE 8000

# Run FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
