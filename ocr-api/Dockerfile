FROM python:3.12-slim

# Install Tesseract OCR and dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    libtesseract-dev \
    libleptonica-dev \
    pkg-config \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set workdir
WORKDIR /docker

# Copy requirements and install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir pytesseract

# Copy application
COPY api.py .

# Expose port
EXPOSE 8000

# Run FastAPI
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8800"]
