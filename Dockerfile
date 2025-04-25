FROM python:3.12-slim

WORKDIR /app

# Install netcat for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends netcat-openbsd && \
  rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Run the application
CMD ["python", "main.py"]
