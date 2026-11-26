"""The search index: one LanceDB table ("chunks") in data/index/. The only module that
talks to the database.

Each row is one chunk: its text, its embedding vector, and where it comes from (document,
category, section, page). LanceDB searches the same table in two ways:
- vector_search(): chunks whose embedding is closest to the query embedding (meaning);
- keyword_search(): chunks containing the query's words, ranked with BM25 (exact terms,
  numbers, article references).
Both take the list of active categories and only look at those chunks.

Public: add_chunks(), delete_document(), list_documents(), vector_search(),
keyword_search(), reset(), compact().
"""

import warnings
from datetime import timedelta

import lancedb
import pyarrow as pa
from lancedb.index import FTS
from lancedb.query import MatchQuery
from lancedb.table import Table

from scanya_ae_afa_updated0209_2_5 import settings

TABLE_NAME = "chunks"

# Row fields returned by the searches and by list_documents() (everything but the vector).
_METADATA_FIELDS = ["id", "doc_id", "category", "source", "section", "page", "added_at"]


def _connect() -> lancedb.DBConnection:
    """Open the database folder (created on first use)."""
    settings.INDEX_DIR.mkdir(parents=True, exist_ok=True)
    return lancedb.connect(settings.INDEX_DIR)


def _open_table() -> Table | None:
    """Return the chunks table, or None if nothing has been indexed yet."""
    try:
        return _connect().open_table(TABLE_NAME)
    except ValueError:  # LanceDB: "Table 'chunks' was not found".
        return None


def _create_table(vector_size: int) -> Table:
    """Create the chunks table for vectors of `vector_size` numbers, with its keyword index."""
    schema = pa.schema(
        [
            ("id", pa.string()),  # "<doc_id>:<chunk number>"
            ("doc_id", pa.string()),  # Same for all chunks of one document.
            ("category", pa.string()),  # Category id from categories.toml.
            ("source", pa.string()),  # File name.
            ("section", pa.string()),  # Headings above the chunk ("4 Bäder › 4.2 Lüftung"), or "".
            ("page", pa.int32()),  # 1-based PDF page; empty for text files.
            ("added_at", pa.string()),  # ISO date and time of the upload.
            ("text", pa.string()),  # The passage as it stands in the document (shown to the user).
            ("search_text", pa.string()),  # File name + section + text: what is embedded and indexed.
            ("vector", pa.list_(pa.float32(), vector_size)),
        ]
    )
    table = _connect().create_table(TABLE_NAME, schema=schema)
    # Keyword (full-text) index on the search text. Words are lower-cased and accents/umlauts
    # are folded ("Brandwände" also matches "brandwande"). No stemming, so it stays
    # language-neutral: word forms like plural/singular are covered by the vector search.
    table.create_index("search_text", config=FTS(lower_case=True, ascii_folding=True, stem=False))
    return table


def _category_filter(categories: list[str]) -> str:
    """SQL filter keeping only chunks of the given categories, e.g. category IN ('a', 'b').

    Safe to build as a string: category ids are validated in categories.py ([a-z0-9_] only).
    """
    quoted = ", ".join(f"'{category}'" for category in categories)
    return f"category IN ({quoted})"


def _without_vector(rows: list[dict]) -> list[dict]:
    """Drop the (long) embedding and the search text from search results; nobody needs them."""
    for row in rows:
        row.pop("vector", None)
        row.pop("search_text", None)
    return rows


def add_chunks(rows: list[dict]) -> None:
    """Add chunk rows (dicts with all table fields, including "vector") to the index.

    The table is created on the first call, sized for the vectors it receives.
    """
    if not rows:
        return
    table = _open_table()
    # "is None", not "or": an empty table (all documents removed) counts as false in Python.
    if table is None:
        table = _create_table(vector_size=len(rows[0]["vector"]))
    table.add(rows)
    # Merge the new rows into the keyword index. (They are searchable before this, too;
    # optimising keeps searches fast as the table grows.)
    table.optimize()


def delete_document(doc_id: str) -> None:
    """Remove all chunks of one document. `doc_id` must be an id made by library.py (hex)."""
    table = _open_table()
    if table is not None and doc_id.isalnum():
        table.delete(f"doc_id = '{doc_id}'")


def list_documents() -> list[dict]:
    """Return one dict per indexed document: doc_id, category, source, added_at, chunks, sections.

    "sections" is the number of different sections recognised in the document (0 = no
    headings were found, so its references can only name the page).
    """
    table = _open_table()
    if table is None:
        return []
    documents: dict[str, dict] = {}
    for row in table.search().select(_METADATA_FIELDS).limit(table.count_rows()).to_list():
        document = documents.setdefault(
            row["doc_id"],
            {"doc_id": row["doc_id"], "category": row["category"], "source": row["source"],
             "added_at": row["added_at"], "chunks": 0, "sections": set()},
        )
        document["chunks"] += 1
        if row["section"]:
            document["sections"].add(row["section"])
    for document in documents.values():
        document["sections"] = len(document["sections"])
    return sorted(documents.values(), key=lambda document: (document["category"], document["source"].lower()))


def vector_search(vector: list[float], categories: list[str], limit: int) -> list[dict]:
    """Return the `limit` chunks closest in meaning to the query vector, best first.

    Only chunks of `categories` are considered (filtered before the search, so the limit
    applies to the active categories). Each row has "_distance" (cosine distance: lower is
    closer).
    """
    table = _open_table()
    if table is None or not categories:
        return []
    query = table.search(vector).distance_type("cosine").where(_category_filter(categories), prefilter=True)
    return _without_vector(query.limit(limit).to_list())


def keyword_search(text: str, categories: list[str], limit: int) -> list[dict]:
    """Return the `limit` chunks that best match the words of `text` (BM25), best first.

    A chunk matches if it contains at least one of the words; rare words (an article number,
    a standard like "4102") weigh more than common ones. The file name and the section
    headings count as words of the chunk too. Each row has "_score" (higher is better).
    MatchQuery treats `text` as plain words, so quotes or operators typed by the user cannot
    break the query.
    """
    table = _open_table()
    if table is None or not categories or not text.strip():
        return []
    query = table.search(MatchQuery(text, "search_text"), query_type="fts")
    query = query.where(_category_filter(categories), prefilter=True)
    return _without_vector(query.limit(limit).to_list())


def reset() -> None:
    """Delete the whole index (the uploaded files in data/library/ are not touched)."""
    _connect().drop_table(TABLE_NAME, ignore_missing=True)


def compact() -> None:
    """Merge the table's files and delete its older versions, so data/index/ stays small.

    LanceDB keeps a new version of the table after every change (13 documents added one by one
    left 315 files, 7.5 MB; compacted: 11 files, under 1 MB). This matters because data/index/
    is committed to git. Only for the build tool (build_index.py): a search running at the same
    time on an older version would fail, so the app does not call it.
    """
    table = _open_table()
    if table is not None:
        with warnings.catch_warnings():  # LanceDB warns about exactly the case described above.
            warnings.simplefilter("ignore", UserWarning)
            table.optimize(cleanup_older_than=timedelta(0), delete_unverified=True)
