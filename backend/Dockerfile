FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip

# Install system dependencies (if needed, e.g., for Pillow or specific libraries)
# RUN apt-get update && apt-get install -y --no-install-recommends some-package
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg libsm6 libxext6 && \
    rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project code into the container
COPY . .

# Expose the port the app runs on (for documentation, not strictly needed with docker-compose ports)
EXPOSE 8000