# Dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
# We use --no-cache-dir to keep the image smaller
RUN pip install --no-cache-dir -r requirements.txt

# Download spacy model (since it's in your requirements)
RUN python -m spacy download en_core_web_sm

# Copy application code
COPY . .

# Expose port
EXPOSE 5000

# Run gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--timeout", "300", "--workers", "2", "app:app"]

# docker-compose.yml
version: '3.8'

services:
  tts-server:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./config.json:/app/config.json
    deploy:
      resources:
        limits:
          memory: 4G  # Increased memory limit due to ML models
        reservations:
          memory: 2G  # Minimum memory reservation
    restart: unless-stopped