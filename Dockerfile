# Use Python 3.9 slim image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .

# Expose port 8080 (Cloud Run default)
EXPOSE 8080

# Set environment variable for Flask
ENV FLASK_APP=main.py
ENV PYTHONUNBUFFERED=1

# Use gunicorn as the production WSGI server
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--timeout", "300", "main:app"]
