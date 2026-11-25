"""Tests of keeping the index in step with data/library/ and of the build_index tool.

Offline like the other tests: fake embeddings, temporary data folders. Run with: uv run pytest
"""

import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding
from pydantic import Field

from scanya_ae_afa_updated0209_2_5 import build_index, library, settings


class FakeEmbeddings(DeterministicFakeEmbedding):
    """Fake embedding model that notes its requests like OpenRouterEmbeddings does."""

    usage: list = Field(default_factory=list)

    def embed_documents(self, texts):
        self.usage.append(
            {"model": settings.EMBEDDING_MODEL, "input_tokens": 10 * len(texts), "output_tokens": 0, "reported_cost": None}
        )
        return super().embed_documents(texts)


@pytest.fixture(autouse=True)
def temporary_data_folders(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "LIBRARY_DIR", tmp_path / "library")
    monkeypatch.setattr(settings, "INDEX_DIR", tmp_path / "index")


def _copy_into_library(category_id: str, file_name: str, text: str) -> None:
    """Put a file into a category folder by hand, as a user would with the file explorer."""
    folder = settings.LIBRARY_DIR / category_id
    folder.mkdir(parents=True, exist_ok=True)
    (folder / file_name).write_text(text, encoding="utf-8")


def _sources() -> list[str]:
    return [document["source"] for document in library.list_documents()]


def test_sync_adds_new_files_and_removes_deleted_ones():
    embeddings = FakeEmbeddings(size=32)
    library.add_document("kept.txt", b"Art. 1 Fire walls must be fire-resistant.", "fire_safety", embeddings)
    library.add_document("deleted.txt", b"Art. 2 Stairs need a handrail.", "general_building", embeddings)
    kept_since = library.list_documents()[0]["added_at"]

    # By hand: one file copied into a folder, one deleted, one left alone.
    _copy_into_library("business", "new.txt", "Offices need a clear height of 2.50 m.")
    (settings.LIBRARY_DIR / "general_building" / "deleted.txt").unlink()

    new_files, removed = library.pending_changes()
    assert [(category_id, path.name) for category_id, path in new_files] == [("business", "new.txt")]
    assert [document["source"] for document in removed] == ["deleted.txt"]
    assert library.estimate_tokens(new_files) > 0

    embeddings.usage.clear()
    assert library.sync_index(embeddings) == (1, 1, [])
    assert sorted(_sources()) == ["kept.txt", "new.txt"]
    assert len(embeddings.usage) == 1  # Only the new file was embedded.
    kept = next(document for document in library.list_documents() if document["source"] == "kept.txt")
    assert kept["added_at"] == kept_since
    assert library.pending_changes() == ([], [])


def test_build_index_tool_asks_before_it_embeds(monkeypatch, capsys):
    monkeypatch.setattr(build_index, "get_embeddings", lambda: FakeEmbeddings(size=32))
    _copy_into_library("business", "new.txt", "Offices need a clear height of 2.50 m.")

    monkeypatch.setattr("builtins.input", lambda prompt: "n")
    build_index.main([])
    assert _sources() == []
    assert "new:     business / new.txt" in capsys.readouterr().out

    monkeypatch.setattr("builtins.input", lambda prompt: "y")
    build_index.main([])
    assert _sources() == ["new.txt"]
    assert "1 document(s) added, 0 removed." in capsys.readouterr().out

    build_index.main([])  # Nothing to do: does not ask.
    assert "up to date" in capsys.readouterr().out

    build_index.main(["--rebuild"])
    output = capsys.readouterr().out
    assert "all 1 file(s) are embedded again" in output and "1 document(s) indexed." in output
    assert "Embedding: 10 tokens, $0.0000002." in output  # 10 tokens at the price in settings.py.
