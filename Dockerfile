# Backend API only (not exposed outside Docker network)
# Build for linux/amd64 so the image runs on Cloud Run (and other x86_64 hosts)
FROM --platform=linux/amd64 python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ ./backend/
COPY ingest.py .
COPY run.py .

# Create directories for data and vector store
RUN mkdir -p /app/data /app/vector_store

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Port: run.py reads PORT from env (default 8080)
EXPOSE 8080

# Run the API server
CMD ["python3", "run.py"]
