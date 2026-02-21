# Lucid Backend - Python 3.13
FROM python:3.13-slim

# Install system dependencies for Pillow text rendering
RUN apt-get update && apt-get install -y \
    libfreetype6-dev \
    libfribidi-dev \
    libharfbuzz-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy font download script and execute during build
COPY download_fonts.py .
RUN python download_fonts.py

# Copy application code
COPY . .

# Fix permissions for the non-root user (1000)
RUN mkdir -p /app/logs/projects /app/data /app/fonts && chown -R 1000:1000 /app
USER 1000

# Expose port
EXPOSE 8000

# Run with hot reload for development
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
