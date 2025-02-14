# Use conda base image
FROM condaforge/mambaforge:latest

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libsndfile1 \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Create conda environment
RUN conda create -n myenv python=3.11 -y

# Install packages with conda first (these are the problematic ones)
RUN conda install -n myenv -c conda-forge \
    blis \
    thinc \
    spacy \
    numpy \
    scipy \
    -y

# Activate conda environment and install remaining packages with pip
SHELL ["conda", "run", "-n", "myenv", "/bin/bash", "-c"]
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.py
ENV FLASK_PORT=10108

EXPOSE 10108

# Run with conda environment
ENTRYPOINT ["conda", "run", "--no-capture-output", "-n", "myenv"]
CMD ["python", "app.py"]