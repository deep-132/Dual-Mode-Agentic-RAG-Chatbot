"""Builds a FAISS index from the markdown knowledge base.

Chunking strategy: each document is split on its `## ` section headers.
The corpus is small policy documents where each section is a
self-contained, citable unit (e.g. "Section 3: Refund Processing") --
splitting any finer would fragment a single rule across chunks and force
retrieval to stitch it back together; splitting any coarser (whole
document per chunk) would drown a specific answer in unrelated sections
and hurt precision.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

SECTION_PATTERN = re.compile(r"^##\s+(.*)$", re.MULTILINE)


@dataclass
class Chunk:
    source: str  # filename, e.g. "returns_policy.md"
    title: str  # document title, e.g. "Northwind Gadgets — Returns and Refunds Policy"
    section: str  # section heading, e.g. "1. Return Window"
    text: str  # section body text (used for both embedding and citation display)


def _parse_document(path: Path) -> list[Chunk]:
    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines()
    title = lines[0].lstrip("# ").strip() if lines else path.stem

    chunks: list[Chunk] = []
    matches = list(SECTION_PATTERN.finditer(raw))
    for i, match in enumerate(matches):
        section_title = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        body = raw[start:end].strip()
        if body:
            chunks.append(Chunk(source=path.name, title=title, section=section_title, text=body))
    return chunks


def load_chunks(documents_dir: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(documents_dir.glob("*.md")):
        chunks.extend(_parse_document(path))
    return chunks


def build_index(documents_dir: Path, index_dir: Path, model_name: str) -> None:
    """Embeds all document chunks and persists a FAISS index + metadata sidecar.

    Idempotent and cheap enough (a few dozen short chunks) to simply run in
    full every time rather than diffing against a previous build.
    """
    index_dir.mkdir(parents=True, exist_ok=True)
    chunks = load_chunks(documents_dir)
    if not chunks:
        raise RuntimeError(f"No .md documents found in {documents_dir}")

    model = SentenceTransformer(model_name)
    embeddings = model.encode(
        [f"{c.title} - {c.section}\n{c.text}" for c in chunks],
        normalize_embeddings=True,
        convert_to_numpy=True,
    ).astype(np.float32)

    # Inner product over normalized vectors == cosine similarity.
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    faiss.write_index(index, str(index_dir / "docs.faiss"))
    (index_dir / "chunks.json").write_text(
        json.dumps([asdict(c) for c in chunks], indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    from app.config import get_settings

    settings = get_settings()
    build_index(settings.documents_dir, settings.index_dir, settings.embedding_model_name)
    print(f"Index built at {settings.index_dir}")
