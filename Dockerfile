# Use official Python runtime as base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy project (manage.py is in pdezzy/)
COPY pdezzy/ .

# Create directories for media and static files
RUN mkdir -p /app/media /app/static

# Expose port
EXPOSE 8006

# Run Daphne server
CMD ["daphne", "-b", "0.0.0.0", "-p", "8006", "pdezzy.asgi:application"]
