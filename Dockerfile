# Use Python 3.11 slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Set work directory
WORKDIR /app

# Install system dependencies including Node.js for Prisma CLI
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    curl \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Install Prisma CLI globally
RUN npm install -g prisma

# Copy requirements first for better caching
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy Prisma schema and setup script
COPY schema.prisma ./ \
     setup_prisma.py ./ \
     import_medicine_data.py ./

# Copy project files
COPY agents/ ./agents/ \
     retrievers/ ./retrievers/ \
     services/ ./services/ \
     configs/ ./configs/ \
     tests/ ./tests/ \
     main.py ./

# Create necessary directories
RUN mkdir -p data/input data/output logs

# Create non-root user and set up home directory
RUN groupadd -r appuser && useradd -r -g appuser -m appuser
RUN chown -R appuser:appuser /app

# Create embedchain and mem0 data directories and set permissions
RUN mkdir -p /home/appuser/.embedchain && \
    mkdir -p /home/appuser/.mem0 && \
    mkdir -p /home/appuser/.cache && \
    chown -R appuser:appuser /home/appuser

USER appuser

# Skip Prisma client generation during build - will be done at runtime

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["python", "main.py", "--mode", "server", "--host", "0.0.0.0", "--port", "8000"]
