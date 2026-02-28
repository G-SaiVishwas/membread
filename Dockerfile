# ChronosMCP Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# Copy application code
COPY src/ ./src/
COPY schema.sql ./

# Create non-root user
RUN useradd -m -u 1000 chronos && \
    chown -R chronos:chronos /app

USER chronos

# Expose port (if needed for HTTP transport)
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV LOG_FORMAT=json

# Run the MCP server
CMD ["python", "-m", "src.main"]
