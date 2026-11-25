"""Embeddings: turn texts into vectors with the OpenRouter embedding model.

A small LangChain-compatible wrapper around the OpenAI SDK client from config.get_client(),
the same way the Sprint 2 labs call the embeddings API. The rest of the app only uses the two
standard methods, embed_documents() and embed_query(), so tests can pass a fake model instead.

Embedding costs money too (per token of the embedded text), so every request is noted in the
object's `usage` list. Who wants to know the cost creates the object with get_embeddings(),
passes it on (library.py, agent.py take it as an argument) and reads `usage` afterwards.

Public: OpenRouterEmbeddings, get_embeddings().
"""

from langchain_core.embeddings import Embeddings

from scanya_ae_afa_updated0209_2_5 import config, settings


class OpenRouterEmbeddings(Embeddings):
    """Embeds texts with settings.EMBEDDING_MODEL through OpenRouter."""

    def __init__(self) -> None:
        # One dict per request made with this object, with the keys of pricing.add_request():
        # "model", "input_tokens", "output_tokens" (always 0) and "reported_cost".
        self.usage: list[dict] = []

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per text, in the same order (EMBEDDING_BATCH_SIZE texts per request)."""
        client = config.get_client("OpenRouter")
        vectors = []
        for start in range(0, len(texts), settings.EMBEDDING_BATCH_SIZE):
            batch = texts[start : start + settings.EMBEDDING_BATCH_SIZE]
            response = client.embeddings.create(model=settings.EMBEDDING_MODEL, input=batch)
            # Each result carries the position of its text in the batch: sort to be safe.
            vectors.extend(item.embedding for item in sorted(response.data, key=lambda item: item.index))
            used = getattr(response, "usage", None)  # Token count, and on OpenRouter also the cost.
            self.usage.append(
                {
                    "model": settings.EMBEDDING_MODEL,
                    "input_tokens": used.prompt_tokens if used else 0,
                    "output_tokens": 0,
                    "reported_cost": getattr(used, "cost", None),
                }
            )
        return vectors

    def embed_query(self, text: str) -> list[float]:
        """Return the vector of one text (a search query)."""
        return self.embed_documents([text])[0]


def get_embeddings() -> OpenRouterEmbeddings:
    """Return the embedding model used for documents and queries (a new object, with empty `usage`)."""
    return OpenRouterEmbeddings()
