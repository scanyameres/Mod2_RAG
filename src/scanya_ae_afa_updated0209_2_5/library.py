"""The document library: add, list and remove knowledge-base documents (no Streamlit code).

Adding a document = read its text -> split into chunks (each with its page and section) ->
embed the chunks -> store them in the index (store.py) -> keep the original file in
data/library/<category id>/.
The original files are the source of truth: rebuild_index() recreates the whole index from
them, e.g. after changing the chunk size or the embedding model in settings.py.

Public: add_document(), remove_document(), list_documents(), rebuild_index().
"""

import hashlib
import re
from datetime import datetime
from pathlib import Path

from langchain_core.embeddings import Embeddings

from scanya_ae_afa_updated0209_2_5 import chunking, settings, store
from scanya_ae_afa_updated0209_2_5.categories import load_categories
from scanya_ae_afa_updated0209_2_5.embeddings import get_embeddings


def _safe_file_name(file_name: str) -> str:
    """Return the bare file name with anything unusual replaced by "_" (no folders, no "..")."""
    name = re.sub(r"[^\w.\- ()]", "_", Path(file_name).name).strip(" .")
    if not name:
        raise ValueError("The file has no usable name.")
    return name[:150]


def _document_id(category_id: str, file_name: str) -> str:
    """Stable id of a document: the same file name in the same category gives the same id."""
    return hashlib.sha1(f"{category_id}/{file_name}".encode()).hexdigest()[:16]


def add_document(file_name: str, data: bytes, category_id: str, embeddings: Embeddings | None = None) -> int:
    """Add one file to a category and return the number of chunks indexed.

    Uploading a file whose name already exists in that category replaces the old version.
    `embeddings` defaults to the OpenRouter embedding model (tests pass a fake one).

    Raises:
        ValueError: unknown category, file too large, unsupported type or no readable text.
    """
    if category_id not in {category.id for category in load_categories()}:
        raise ValueError(f"Unknown category '{category_id}'.")
    if len(data) > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise ValueError(f"The file is larger than {settings.MAX_UPLOAD_MB} MB.")
    file_name = _safe_file_name(file_name)

    chunks = chunking.split_pages(chunking.read_pages(file_name, data))
    embeddings = embeddings or get_embeddings()
    # What is searched is the passage together with its file name and section headings, so a
    # question like "ventilation in bathrooms" also finds a passage that only says "40 m³/h"
    # below the heading "Bäder › Lüftung".
    title = Path(file_name).stem
    search_texts = [f"{title}\n{chunk.section}\n{chunk.text}" for chunk in chunks]
    vectors = embeddings.embed_documents(search_texts)

    doc_id = _document_id(category_id, file_name)
    added_at = datetime.now().isoformat(timespec="seconds")
    rows = [
        {
            "id": f"{doc_id}:{number}",
            "doc_id": doc_id,
            "category": category_id,
            "source": file_name,
            "section": chunk.section,
            "page": chunk.page,
            "added_at": added_at,
            "text": chunk.text,
            "search_text": search_text,
            "vector": vector,
        }
        for number, (chunk, search_text, vector) in enumerate(zip(chunks, search_texts, vectors))
    ]
    store.delete_document(doc_id)  # Replace an earlier version of the same file, if any.
    store.add_chunks(rows)

    # Keep the original, so the index can be rebuilt later.
    folder = settings.LIBRARY_DIR / category_id
    folder.mkdir(parents=True, exist_ok=True)
    (folder / file_name).write_bytes(data)
    return len(rows)


def list_documents() -> list[dict]:
    """Return the indexed documents (dicts: doc_id, category, source, added_at, chunks, sections)."""
    return store.list_documents()


def remove_document(doc_id: str) -> None:
    """Remove a document from the index and delete its file from data/library/."""
    for document in store.list_documents():
        if document["doc_id"] == doc_id:
            store.delete_document(doc_id)
            (settings.LIBRARY_DIR / document["category"] / document["source"]).unlink(missing_ok=True)
            return


def rebuild_index(embeddings: Embeddings | None = None) -> tuple[int, list[str]]:
    """Delete the index and re-add every file found in data/library/<category id>/.

    Use after changing CHUNK_SIZE / CHUNK_OVERLAP / EMBEDDING_MODEL, or after copying files
    into the library folders by hand. Every chunk is embedded again (API cost).

    Returns:
        (number of documents indexed, messages for the files that failed).
    """
    store.reset()
    indexed, problems = 0, []
    for category in load_categories():
        folder = settings.LIBRARY_DIR / category.id
        for path in sorted(folder.glob("*")) if folder.is_dir() else []:
            if not path.is_file() or path.name.startswith("."):
                continue
            try:
                add_document(path.name, path.read_bytes(), category.id, embeddings)
                indexed += 1
            except Exception as error:  # Keep going: one bad file must not stop the rebuild.
                problems.append(f"{category.name} / {path.name}: {error}")
    return indexed, problems
