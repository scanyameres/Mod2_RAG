"""Search the knowledge base. By default a hybrid search: vector search (meaning) and keyword
search (exact words) combined into one ranked list, restricted to the active categories.

Why both: a question like "how far must a building be from the plot boundary?" is found by
meaning, while "Art. 6 Abs. 5" or "DIN 4102-4" must match the exact characters, which
embeddings are bad at. Each search returns its own ranking, and Reciprocal Rank Fusion (RRF)
merges them: a chunk scores 1 / (60 + rank) for every list it appears in, so chunks found by
both searches come first. Ranks are used instead of the raw scores because BM25 scores and
cosine distances are on different scales.

The keyword search can be switched off (Settings in the app); then only the vector ranking
is used.

Match values. Every hit also carries the raw value of each search, for display:
- similarity: 1 - cosine distance between the query and the passage. 1 = same meaning,
  around 0 = unrelated. Comparable between searches.
- keyword_score: the BM25 score. Higher = the query's words are rarer and more frequent in
  the passage. No fixed scale: only comparable within one search.
Neither is a probability that the passage answers the question.

Public: Hit, search(), reciprocal_rank_fusion().
"""

from dataclasses import dataclass

from langchain_core.embeddings import Embeddings

from scanya_ae_afa_updated0209_2_5 import settings, store
from scanya_ae_afa_updated0209_2_5.embeddings import get_embeddings


@dataclass(frozen=True)
class Hit:
    """One retrieved chunk, with where it comes from and how each search ranked it."""

    chunk_id: str
    doc_id: str
    source: str  # File name.
    category: str  # Category id.
    section: str  # Headings above the passage, e.g. "4 Bäder › 4.2 Lüftung"; "" if unknown.
    page: int | None
    text: str
    score: float  # RRF score (higher is better).
    vector_rank: int | None  # 1 = best match by meaning; None = not found by that search.
    keyword_rank: int | None  # 1 = best match by keywords; None = not found by that search.
    similarity: float | None = None  # Match by meaning, see "Match values" above; None like vector_rank.
    keyword_score: float | None = None  # BM25 score; None like keyword_rank.


def reciprocal_rank_fusion(rankings: list[list[str]], constant: int = settings.RRF_CONSTANT) -> dict[str, float]:
    """Merge several rankings (lists of ids, best first) into one score per id.

    score(id) = sum over the rankings containing it of 1 / (constant + rank), rank starting at 1.
    """
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, item_id in enumerate(ranking, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + 1 / (constant + rank)
    return scores


def search(
    query: str,
    categories: list[str],
    hybrid: bool = True,
    k: int = settings.TOP_K,
    embeddings: Embeddings | None = None,
) -> list[Hit]:
    """Return the `k` best chunks for `query` among the given category ids.

    hybrid=True: one vector search and one keyword search (CANDIDATES_PER_SEARCH chunks each),
    merged with RRF. hybrid=False: the vector search alone (the keyword ranking stays empty,
    so the result is simply the vector ranking).
    `embeddings` defaults to the OpenRouter embedding model; tests pass a fake one to run
    without an API key.
    """
    if not query.strip() or not categories:
        return []
    embeddings = embeddings or get_embeddings()
    limit = settings.CANDIDATES_PER_SEARCH

    vector_rows = store.vector_search(embeddings.embed_query(query), categories, limit)
    keyword_rows = store.keyword_search(query, categories, limit) if hybrid else []

    vector_ids = [row["id"] for row in vector_rows]
    keyword_ids = [row["id"] for row in keyword_rows]
    similarities = {row["id"]: round(1 - row["_distance"], 3) for row in vector_rows}
    keyword_scores = {row["id"]: round(row["_score"], 2) for row in keyword_rows}
    scores = reciprocal_rank_fusion([vector_ids, keyword_ids])
    rows_by_id = {row["id"]: row for row in vector_rows + keyword_rows}

    best_ids = sorted(scores, key=scores.get, reverse=True)[:k]
    return [
        Hit(
            chunk_id=chunk_id,
            doc_id=rows_by_id[chunk_id]["doc_id"],
            source=rows_by_id[chunk_id]["source"],
            category=rows_by_id[chunk_id]["category"],
            section=rows_by_id[chunk_id]["section"],
            page=rows_by_id[chunk_id]["page"],
            text=rows_by_id[chunk_id]["text"],
            score=scores[chunk_id],
            vector_rank=vector_ids.index(chunk_id) + 1 if chunk_id in vector_ids else None,
            keyword_rank=keyword_ids.index(chunk_id) + 1 if chunk_id in keyword_ids else None,
            similarity=similarities.get(chunk_id),
            keyword_score=keyword_scores.get(chunk_id),
        )
        for chunk_id in best_ids
    ]
