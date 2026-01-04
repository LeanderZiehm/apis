FROM python:3.11-slim

WORKDIR /docker

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api.py .
COPY static/ static/

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8803"]
