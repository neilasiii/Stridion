# Multi-stage build for running coach service
FROM python:3.11-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY .claude/ ./.claude/
COPY data/ ./data/
COPY bin/ ./bin/
COPY config/ ./config/
COPY alembic/ ./alembic/
COPY alembic.ini ./alembic.ini
COPY docker-entrypoint.sh ./docker-entrypoint.sh

# Create necessary directories with open permissions
# (actual user will be set via docker-compose user: directive)
RUN mkdir -p /app/data/health \
    /app/data/athlete \
    /app/data/library \
    /app/data/calendar \
    /app/data/plans \
    /app/data/frameworks && \
    chmod -R 777 /app/data && \
    chmod +x /app/docker-entrypoint.sh

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/api/v1/health')" || exit 1

# Run the entrypoint script (handles DB init + starts web service)
CMD ["/app/docker-entrypoint.sh"]
