FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install deps first for layer caching
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock

# WORKDIR /app + COPY app/ ./app/ means `from app.xxx` resolves from /app
COPY app/ ./app/
COPY ui/  ./ui/

RUN mkdir -p /app/data

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
