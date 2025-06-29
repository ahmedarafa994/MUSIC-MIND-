FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ffmpeg \
        libsndfile1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create necessary directories
# TEMP_PATH is defined in config.py for temporary audio processing files.
RUN mkdir -p /tmp/audio_processing
# If app creates logs directory, ensure its parent is writable by appuser or create it here owned by appuser
# RUN mkdir -p /app/logs && chown appuser:appuser /app/logs


# Create non-root user and group
RUN groupadd -r appuser && useradd --no-log-init -r -g appuser appuser

# Change ownership of the app directory and any created paths
RUN chown -R appuser:appuser /app && \
    chown -R appuser:appuser /tmp/audio_processing

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]