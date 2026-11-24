"""Embeddings: turn texts into vectors with the OpenRouter embedding model.

A small LangChain-compatible wrapper around the OpenAI SDK client from config.get_client(),
the same way the Sprint 2 labs call the embeddings API. The rest of the app only uses the two
standard methods, embed_documents() and embed_query(), so tests can pass a fake model instead.

Public: OpenRouterEmbeddings, get_embeddings().
"""

from langchain_core.embeddings import Embeddings

from scanya_ae_afa_updated0209_2_5 import config, settings


class OpenRouterEmbeddings(Embeddings):
    """Embeds texts with settings.EMBEDDING_MODEL through OpenRouter."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per text, in the same order (EMBEDDING_BATCH_SIZE texts per request)."""
        client = config.get_client("OpenRouter")
        vectors = []
        for start in range(0, len(texts), settings.EMBEDDING_BATCH_SIZE):
            batch = texts[start : start + settings.EMBEDDING_BATCH_SIZE]
            response = client.embeddings.create(model=settings.EMBEDDING_MODEL, input=batch)
            # Each result carries the position of its text in the batch: sort to be safe.
            vectors.extend(item.embedding for item in sorted(response.data, key=lambda item: item.index))
        return vectors

    def embed_query(self, text: str) -> list[float]:
        """Return the vector of one text (a search query)."""
        return self.embed_documents([text])[0]


def get_embeddings() -> Embeddings:
    """Return the embedding model used for documents and queries."""
    return OpenRouterEmbeddings()
