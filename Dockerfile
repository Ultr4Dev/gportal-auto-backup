FROM python:3.10-slim

# Install necessary packages and Firefox
RUN apt-get update

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ./src /app
WORKDIR /app

# Command to run your application
CMD ["python3", "selenium-docker.py"]
