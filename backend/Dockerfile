FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=8080

# Install system dependencies needed for OpenCV, Kokoro/Soundfile (espeak-ng is mandatory for Kokoro)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1 \
    libglib2.0-0 \
    libsndfile1 \
    espeak-ng \
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

# Pre-download Hugging Face and NLTK models during build so the container boots in 2 seconds without network delays
RUN uv run python -c "import nltk; nltk.download('punkt_tab', quiet=True); from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2'); from kokoro import KPipeline; KPipeline(lang_code='a', repo_id='hexgrad/Kokoro-82M')"

# Copy all application code, models, and assets
COPY . .

EXPOSE 8080

CMD ["sh", "-c", "uv run uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080} --timeout-keep-alive 65"]
