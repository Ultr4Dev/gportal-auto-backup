FROM python:3.10-slim

# Install necessary packages and Firefox
RUN apt-get update && apt-get install -y --no-install-recommends \
    firefox-esr curl wget tar \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for Firefox
ENV FIREFOX_BIN="/usr/bin/firefox-esr"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app
WORKDIR /app

# Command to run your application
CMD ["python3", "selenium-docker.py"]
