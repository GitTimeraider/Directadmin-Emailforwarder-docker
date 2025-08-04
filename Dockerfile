FROM python:3.13-slim

# Default UID and GID (can be overridden)
ARG USER_UID=1000
ARG USER_GID=1000

WORKDIR /app

# Install system dependencies and create user
RUN apt-get update && apt-get install -y \
    gcc \
    gosu \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -g ${USER_GID} appuser \
    && useradd -m -u ${USER_UID} -g appuser appuser

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=appuser:appuser . .

# Create volume for database with proper permissions
RUN mkdir -p /app/data && chown -R appuser:appuser /app/data
VOLUME ["/app/data"]

# Set environment variables
ENV FLASK_APP=app.main:create_app
ENV PYTHONUNBUFFERED=1
ENV USER_UID=${USER_UID}
ENV USER_GID=${USER_GID}

# Copy and set permissions for entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 5000

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "app.main:create_app()"]
