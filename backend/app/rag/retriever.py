"""Loads the prebuilt FAISS index once and serves similarity search queries."""
from __future__ import annotations

import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from app.rag.ingest import Chunk, build_index
from app.schemas import Citation


class DocumentRetriever:
    def __init__(self, index_dir: Path, documents_dir: Path, model_name: str) -> None:
        self._index_dir = index_dir
        self._documents_dir = documents_dir
        self._model_name = model_name
        self._model: SentenceTransformer | None = None
        self._index: faiss.Index | None = None
        self._chunks: list[Chunk] = []

    def load(self) -> None:
        index_path = self._index_dir / "docs.faiss"
        chunks_path = self._index_dir / "chunks.json"
        if not index_path.exists() or not chunks_path.exists():
            # Safety net for local dev (`uvicorn app.main:app`) without a manual
            # build step first; production images prebuild the index instead.
            build_index(self._documents_dir, self._index_dir, self._model_name)

        self._index = faiss.read_index(str(index_path))
        raw_chunks = json.loads(chunks_path.read_text(encoding="utf-8"))
        self._chunks = [Chunk(**c) for c in raw_chunks]
        self._model = SentenceTransformer(self._model_name)

    def search(self, query: str, top_k: int) -> list[Citation]:
        if self._index is None or self._model is None:
            raise RuntimeError("DocumentRetriever.load() must be called before search()")

        query_vec = self._model.encode([query], normalize_embeddings=True, convert_to_numpy=True)
        scores, indices = self._index.search(query_vec.astype(np.float32), top_k)

        results: list[Citation] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            chunk = self._chunks[idx]
            results.append(
                Citation(source=chunk.source, section=chunk.section, text=chunk.text, score=float(score))
            )
        return results
