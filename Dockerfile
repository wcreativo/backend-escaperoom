FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Make init script executable
RUN chmod +x init.sh

# Expose port
EXPOSE 8000

# Run initialization and then gunicorn
CMD ["sh", "-c", "./init.sh && gunicorn --bind 0.0.0.0:8000 --workers 3 escape_rooms_backend.wsgi:application"]
