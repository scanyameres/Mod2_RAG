"""The document library: add, list and remove knowledge-base documents (no Streamlit code).

Adding a document = read its text -> split into chunks (each with its page and section) ->
embed the chunks -> store them in the index (store.py) -> keep the original file in
data/library/<category id>/.
The original files are the source of truth, and the index is made from them in two ways:
- sync_index() brings the index up to date with the folder: files that are not in the index
  yet are embedded, documents whose file was deleted are removed from it. Files are
  recognised by category folder + file name, so a file that was replaced by another one
  with the same name is NOT noticed (upload it on the Knowledge base page, or rebuild).
- rebuild_index() embeds everything again, e.g. after changing the chunk size or the
  embedding model in settings.py.
Nothing happens by itself when files are copied into or deleted from the folders: one of
the two must be run (build_index.py, or the Knowledge base page for the rebuild).

Public: add_document(), remove_document(), list_documents(), library_files(),
pending_changes(), estimate_tokens(), sync_index(), rebuild_index().
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


def _read_chunks(file_name: str, data: bytes) -> tuple[list[chunking.Chunk], list[str]]:
    """Read a file and split it: (chunks, the text that is embedded and searched for each chunk).

    What is searched is the passage together with its file name and section headings, so a
    question like "ventilation in bathrooms" also finds a passage that only says "40 m³/h"
    below the heading "Bäder › Lüftung".
    """
    chunks = chunking.split_pages(chunking.read_pages(file_name, data))
    title = Path(file_name).stem
    return chunks, [f"{title}\n{chunk.section}\n{chunk.text}" for chunk in chunks]


def add_document(file_name: str, data: bytes, category_id: str, embeddings: Embeddings | None = None) -> int:
    """Add one file to a category and return the number of chunks indexed.

    Uploading a file whose name already exists in that category replaces the old version.
    `embeddings` defaults to the OpenRouter embedding model (tests pass a fake one).

    Raises:
        ValueError: unknown category, file too large, unsupported type or no readable text.
    """
    if category_id not in {category.id for category in load_categories()}:
        raise ValueError(f"Unknown category '{category_id}'.")
    file_name = _safe_file_name(file_name)

    chunks, search_texts = _read_chunks(file_name, data)
    embeddings = embeddings or get_embeddings()
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


def library_files() -> list[tuple[str, Path]]:
    """Every file in data/library/<category id>/, as (category id, path).

    Folders that are not a category of categories.toml are ignored.
    """
    files = []
    for category in load_categories():
        folder = settings.LIBRARY_DIR / category.id
        for path in sorted(folder.glob("*")) if folder.is_dir() else []:
            if path.is_file() and not path.name.startswith("."):
                files.append((category.id, path))
    return files


def pending_changes() -> tuple[list[tuple[str, Path]], list[dict]]:
    """Compare data/library/ with the index, by category + file name.

    Returns:
        (new files, as (category id, path): in the folder but not in the index;
         removed documents, as dicts of list_documents(): in the index, file no longer there).
    """
    indexed = {document["doc_id"]: document for document in store.list_documents()}
    in_folder = {
        _document_id(category_id, _safe_file_name(path.name)): (category_id, path)
        for category_id, path in library_files()
    }
    new_files = [file for doc_id, file in in_folder.items() if doc_id not in indexed]
    removed = [document for doc_id, document in indexed.items() if doc_id not in in_folder]
    return new_files, removed


def estimate_tokens(files: list[tuple[str, Path]]) -> int:
    """Roughly how many tokens embedding these files takes (no API call).

    The text that would be embedded is counted with about 4 characters per token. Files
    that cannot be read count as 0; they are reported when they are embedded.
    """
    characters = 0
    for _, path in files:
        try:
            _, search_texts = _read_chunks(path.name, path.read_bytes())
        except ValueError:
            continue
        characters += sum(map(len, search_texts))
    return characters // 4


def _add_files(files: list[tuple[str, Path]], embeddings: Embeddings | None) -> tuple[int, list[str]]:
    """Add files of the library folders to the index: (number added, messages for those that failed)."""
    added, problems = 0, []
    for category_id, path in files:
        try:
            add_document(path.name, path.read_bytes(), category_id, embeddings)
            added += 1
        except Exception as error:  # Keep going: one bad file must not stop the others.
            problems.append(f"{category_id} / {path.name}: {error}")
    return added, problems


def sync_index(embeddings: Embeddings | None = None) -> tuple[int, int, list[str]]:
    """Bring the index up to date with data/library/ (see pending_changes()).

    New files are embedded (API cost); documents whose file was deleted are removed from
    the index. Documents that are already in the index are not touched.

    Returns:
        (documents added, documents removed, messages for the files that failed).
    """
    new_files, removed = pending_changes()
    for document in removed:
        store.delete_document(document["doc_id"])
    added, problems = _add_files(new_files, embeddings)
    return added, len(removed), problems


def rebuild_index(embeddings: Embeddings | None = None) -> tuple[int, list[str]]:
    """Delete the index and re-add every file found in data/library/<category id>/.

    Use after changing CHUNK_SIZE / CHUNK_OVERLAP / EMBEDDING_MODEL or the heading rules of
    chunking.py. Every chunk is embedded again (API cost), so ask the user before calling it.

    Returns:
        (number of documents indexed, messages for the files that failed).
    """
    store.reset()
    return _add_files(library_files(), embeddings)
