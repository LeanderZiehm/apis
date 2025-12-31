# Use official Python base image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY api.py .

# Expose port and run the app
EXPOSE 8801
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8801"]
