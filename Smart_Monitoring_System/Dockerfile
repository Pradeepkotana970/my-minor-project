# Smart Monitoring System v2.0 - Dockerfile
# Production-ready container for Smart Monitoring System

FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # OpenCV dependencies
    libsm6 libxext6 libxrender-dev \
    # Additional utilities
    libgomp1 \
    # Build tools (for pip packages)
    build-essential \
    # Audio support
    libportaudio2 \
    # Cleanup
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs alerts/unknown_persons dataset trainer

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/api/status', timeout=5)" || exit 1

# Default command: Start web dashboard
CMD ["python", "app_dashboard.py"]

# Alternative commands can be run as:
# docker run ... python app_enhanced_v2.py  # For standalone mode
# docker run ... python train_model.py      # For training
