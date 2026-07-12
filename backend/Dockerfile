FROM python:3.12-slim

WORKDIR /app

# System deps for faiss / sentence-transformers wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY data ./data
COPY scripts ./scripts

# Prebuild the FAISS index at image-build time (downloads the embedding
# model once here too) so container startup is fast and a bad document
# fails the build instead of the first request.
RUN python -m scripts.build_index

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
