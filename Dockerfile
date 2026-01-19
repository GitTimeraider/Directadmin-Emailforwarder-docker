FROM python:3.15.0a5-slim

# Default UID and GID (can be overridden)
ARG USER_UID=1000
ARG USER_GID=1000

WORKDIR /app

# Install system dependencies and create user
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    gosu \
    python3-dev \
    libffi-dev \
    zlib1g-dev \
    libjpeg-dev \
    libpng-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libopenjp2-7-dev \
    libtiff-dev \
    libwebp-dev \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -g ${USER_GID} appuser \
    && useradd -m -u ${USER_UID} -g appuser appuser

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code with correct ownership
COPY --chown=appuser:appuser app /app/app
COPY --chown=appuser:appuser static /app/static
COPY --chown=appuser:appuser docker-entrypoint.sh /usr/local/bin/

# Create data directory with proper permissions
RUN mkdir -p /app/data && chown -R appuser:appuser /app/data

# Make entrypoint executable
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Set environment variables
ENV FLASK_APP=app.main:create_app
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

VOLUME ["/app/data"]
EXPOSE 5000

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
# Use --preload so that db.create_all runs once before forking workers (avoids SQLite lock/race)
CMD ["gunicorn", "--preload", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "--access-logfile", "-", "--error-logfile", "-", "app.main:create_app()"]
