#!/usr/bin/env python
"""Standalone entrypoint to prebuild the FAISS document index.

Run at Docker build time so container startup doesn't pay the embedding
cost on every cold start/restart, and so a build failure (e.g. a malformed
document) is caught in CI/image-build rather than at request time.
"""
from app.config import get_settings
from app.rag.ingest import build_index

if __name__ == "__main__":
    settings = get_settings()
    build_index(settings.documents_dir, settings.index_dir, settings.embedding_model_name)
    print(f"FAISS index built at {settings.index_dir}")
