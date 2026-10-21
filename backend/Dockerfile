FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    HF_HOME=/app/.cache/huggingface \
    PORT=8080

# Install system dependencies needed for OpenCV, Kokoro/Soundfile, PyTorch
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1 \
    libglib2.0-0 \
    libsndfile1 \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv package manager
RUN pip install --no-cache-dir uv

# Copy dependency specifications first to leverage Docker layer caching
COPY pyproject.toml uv.lock ./

# Install python dependencies
RUN uv sync --frozen

# Copy all application code, models, and assets
COPY . .

# Hugging Face Spaces expects non-root user (UID 1000)
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/.cache && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8080

CMD ["sh", "-c", "uv run uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
