# Use official Python runtime as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create kb directory if it doesn't exist
RUN mkdir -p kb

# Expose port (Railway/K8s will set PORT env var)
EXPOSE 8000

# Run the application
CMD ["uvicorn", "ca_agent_tools:app", "--host", "0.0.0.0", "--port", "8000"]
