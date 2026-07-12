from app.config import BASE_DIR
from app.rag.ingest import load_chunks


def test_loads_all_documents_and_splits_by_section(tmp_path):
    doc = tmp_path / "sample_policy.md"
    doc.write_text(
        "# Sample Policy\n\n"
        "## 1. First Section\n"
        "First section body text.\n\n"
        "## 2. Second Section\n"
        "Second section body text.\n",
        encoding="utf-8",
    )

    chunks = load_chunks(tmp_path)

    assert len(chunks) == 2
    assert chunks[0].source == "sample_policy.md"
    assert chunks[0].title == "Sample Policy"
    assert chunks[0].section == "1. First Section"
    assert "First section body text" in chunks[0].text
    assert chunks[1].section == "2. Second Section"


def test_real_document_corpus_parses_into_multiple_sections():
    # Reference the documents path directly rather than via get_settings() --
    # this test is about chunking logic, not Azure config, and shouldn't
    # start requiring credentials just because it shares a module with them.
    documents_dir = BASE_DIR / "data" / "documents"
    chunks = load_chunks(documents_dir)
    sources = {c.source for c in chunks}
    assert "returns_policy.md" in sources
    assert "warranty_policy.md" in sources
    assert len(chunks) >= 10
