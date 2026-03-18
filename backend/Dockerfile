# Multi-stage build: download model at build time, zero cold-start overhead
FROM python:3.11-slim as builder

WORKDIR /app
COPY requirements.txt .

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*
# Install CPU-only PyTorch FIRST — prevents sentence-transformers from pulling
# the full CUDA build (~2.5 GB of nvidia-* libs) on a CPU-only server.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the embedding model (~430 MB) into the image
# This runs once at build time, so the container starts with zero embedding API latency
RUN python -c "from langchain_huggingface import HuggingFaceEmbeddings; \
               model = HuggingFaceEmbeddings(model_name='BAAI/bge-base-en-v1.5'); \
               print('✅ Embedding model pre-downloaded and cached')"

# Final stage: runtime image with all dependencies + cached model
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages and executables from builder
# site-packages: Python libraries; bin: executables (uvicorn, pip, etc.); cache: BAAI model
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages/
COPY --from=builder /usr/local/bin /usr/local/bin/
COPY --from=builder /root/.cache /root/.cache/

# Copy app code
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY .env* ./

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Create data dir at startup (volume mount happens at runtime, not build time)
# then launch uvicorn
CMD ["sh", "-c", "mkdir -p /app/data && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
