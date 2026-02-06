# Backend API only (not exposed outside Docker network)
FROM python:3.12-slim

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

# Create directories for data and vector store
RUN mkdir -p /app/data /app/vector_store

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Port only used inside the container network (not published)
EXPOSE 8000

# Run the API server
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
