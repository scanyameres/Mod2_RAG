"""Tests of the user history and the cost calculation that run offline: no API key, no network.

The price list of OpenRouter is replaced by a fixed one, the chat model by a fake that reports
token counts, and the data folders by a temporary folder. The login itself (auth.py) is
Streamlit code and is not tested here. Run with: uv run pytest
"""

from dataclasses import asdict

import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from pydantic import Field

from scanya_ae_afa_updated0209_2_5 import agent, config, library, pricing, settings, user_store
from scanya_ae_afa_updated0209_2_5.embeddings import OpenRouterEmbeddings
from scanya_ae_afa_updated0209_2_5.workspace import Workspace

# USD per token (input, output). "priced/model" stands for any model in the OpenRouter list.
PRICES = {"priced/model": (1e-6, 4e-6)}


@pytest.fixture(autouse=True)
def offline(tmp_path, monkeypatch):
    """Temporary data folders and a fixed price list instead of the OpenRouter endpoint."""
    monkeypatch.setattr(settings, "LIBRARY_DIR", tmp_path / "library")
    monkeypatch.setattr(settings, "INDEX_DIR", tmp_path / "index")
    monkeypatch.setattr(settings, "USERS_DIR", tmp_path / "users")
    monkeypatch.setattr(pricing, "_all_model_prices", lambda: PRICES)


# --- pricing.py ---


def test_request_cost_prefers_the_reported_cost():
    assert pricing.request_cost("priced/model", 1000, 100, reported_cost=0.5) == 0.5
    assert pricing.request_cost("priced/model", 1000, 100) == pytest.approx(1000 * 1e-6 + 100 * 4e-6)
    assert pricing.request_cost("unknown/model", 1000, 100) is None


def test_estimate_of_one_answer_per_model(monkeypatch):
    monkeypatch.setattr(settings, "TYPICAL_ANSWER_INPUT_TOKENS", 1000)
    monkeypatch.setattr(settings, "TYPICAL_ANSWER_OUTPUT_TOKENS", 100)
    assert pricing.estimate_answer_cost("priced/model") == pytest.approx(1000 * 1e-6 + 100 * 4e-6)
    assert pricing.estimate_answer_cost("unknown/model") is None


def test_usage_adds_up_per_model():
    usage = {}
    pricing.add_request(usage, "priced/model", 1000, 100)
    pricing.add_request(usage, "priced/model", 2000, 200, reported_cost=0.01)
    pricing.add_request(usage, "unknown/model", 500, 50)
    assert usage["priced/model"] == {
        "requests": 2,
        "input_tokens": 3000,
        "output_tokens": 300,
        "cost": pytest.approx(0.0014 + 0.01),
        "unpriced": 0,
    }
    assert usage["unknown/model"]["unpriced"] == 1 and usage["unknown/model"]["cost"] == 0
    assert pricing.total_cost(usage) == pytest.approx(0.0114)
    assert pricing.total_tokens(usage) == 3850


def test_format_usd():
    assert pricing.format_usd(0.00038) == "\\$0.00038"
    assert pricing.format_usd(1.5) == "\\$1.500"
    assert pricing.format_usd(0) == "\\$0.00000"
    assert pricing.format_usd(0.0000004) == "\\$0.0000004"  # One search query: still visible.
    assert pricing.format_usd(0.02, markdown=False) == "$0.020"


def test_embedding_requests_are_noted_and_priced(monkeypatch):
    """OpenRouterEmbeddings notes tokens and cost of each request; pricing knows the embedding price."""

    class FakeEmbeddingsApi:
        def create(self, model, input):
            items = [type("Item", (), {"index": i, "embedding": [1.0]}) for i, _ in enumerate(input)]
            usage = type("Usage", (), {"prompt_tokens": 7 * len(input), "cost": 0.5})
            return type("Response", (), {"data": items, "usage": usage})

    monkeypatch.setattr(config, "get_client", lambda provider: type("Client", (), {"embeddings": FakeEmbeddingsApi()}))
    embeddings = OpenRouterEmbeddings()
    embeddings.embed_query("minimum distance")
    assert embeddings.usage == [
        {"model": settings.EMBEDDING_MODEL, "input_tokens": 7, "output_tokens": 0, "reported_cost": 0.5}
    ]
    # Without a reported cost: tokens x the price in settings.py.
    monkeypatch.setattr(settings, "EMBEDDING_PRICE_PER_MILLION_TOKENS", 0.02)
    assert pricing.request_cost(settings.EMBEDDING_MODEL, 1_000_000, 0) == pytest.approx(0.02)


# --- agent.py: usage events ---


class FakeToolCallingModel(GenericFakeChatModel):
    """Fake chat model that replays prepared messages. Tools are accepted and ignored."""

    def bind_tools(self, tools, **kwargs):
        return self


def test_agent_reports_the_usage_of_every_model_request():
    embeddings = DeterministicFakeEmbedding(size=32)
    library.add_document("code.txt", b"Art. 6. Die Tiefe betraegt 0,4 H, mindestens 3 m.", "general_building", embeddings)
    tokens = {"input_tokens": 900, "output_tokens": 40, "total_tokens": 940}
    replies = [
        AIMessage(
            content="",
            tool_calls=[{"name": "search_documentation", "args": {"query": "Abstandsflaeche"}, "id": "call_1"}],
            usage_metadata=tokens,
            response_metadata={"cost": 0.002},  # As OpenRouter reports it.
        ),
        AIMessage(content="At least 3 m [1].", usage_metadata=tokens),  # No reported cost.
    ]
    events = list(
        agent.answer_question(
            "Which distance?",
            history=[],
            workspace=Workspace(),
            active_category_ids=["general_building"],
            model_name="priced/model",
            chat_model=FakeToolCallingModel(messages=iter(replies)),
            embeddings=embeddings,
        )
    )
    assert [event.kind for event in events] == ["usage", "tool_call", "tool_result", "usage", "answer"]

    usage = {}
    for event in events:
        if event.kind == "usage":
            pricing.add_request(usage, **event.usage)
    assert usage["priced/model"]["requests"] == 2
    assert usage["priced/model"]["cost"] == pytest.approx(0.002 + 900 * 1e-6 + 40 * 4e-6)


def test_agent_reports_the_embedding_request_of_a_search():
    class NotingEmbeddings(DeterministicFakeEmbedding):
        """Fake embedding model that notes its requests like OpenRouterEmbeddings does."""

        usage: list = Field(default_factory=list)

        def embed_query(self, text):
            self.usage.append(
                {"model": settings.EMBEDDING_MODEL, "input_tokens": 5, "output_tokens": 0, "reported_cost": None}
            )
            return super().embed_query(text)

    embeddings = NotingEmbeddings(size=32)
    library.add_document("code.txt", b"Art. 6. Die Tiefe betraegt 0,4 H, mindestens 3 m.", "general_building", embeddings)
    replies = [
        AIMessage(content="", tool_calls=[{"name": "search_documentation", "args": {"query": "Tiefe"}, "id": "call_1"}]),
        AIMessage(content="At least 3 m [1]."),
    ]
    events = list(
        agent.answer_question(
            "Which distance?",
            history=[],
            workspace=Workspace(),
            active_category_ids=["general_building"],
            chat_model=FakeToolCallingModel(messages=iter(replies)),
            embeddings=embeddings,
        )
    )
    assert [event.kind for event in events] == ["tool_call", "tool_result", "usage", "answer"]
    usage = {}
    pricing.add_request(usage, **events[2].usage)
    assert usage[settings.EMBEDDING_MODEL]["input_tokens"] == 5
    assert usage[settings.EMBEDDING_MODEL]["cost"] == pytest.approx(5 * settings.EMBEDDING_PRICE_PER_MILLION_TOKENS / 1e6)


# --- user_store.py ---


def _conversation(conversation_id: str, title: str, cost: float) -> dict:
    workspace = Workspace(project_notes="Hotel, 40 rooms", document_title="Checklist", document="- Rule [1]")
    return {
        "id": conversation_id,
        "title": title,
        "messages": [{"role": "user", "content": title}, {"role": "assistant", "content": "Answer", "steps": [], "sources": []}],
        "workspace": asdict(workspace),
        "settings": {"active_categories": ["general_building"], "hybrid": True, "model_name": "priced/model"},
        "usage": {"priced/model": {"requests": 1, "input_tokens": 10, "output_tokens": 5, "cost": cost, "unpriced": 0}},
    }


def test_history_is_saved_per_user_and_can_be_restored():
    assert user_store.load_conversations("sergi") == []
    user_store.save_conversation("sergi", _conversation("a", "First question", 0.01))
    user_store.save_conversation("sergi", _conversation("b", "Second question", 0.02))
    user_store.save_conversation("Anna", _conversation("c", "Another user", 0.5))

    conversations = user_store.load_conversations("sergi")
    assert {conversation["id"] for conversation in conversations} == {"a", "b"}
    assert user_store.total_cost("sergi") == pytest.approx(0.03)
    assert user_store.total_cost("anna") == pytest.approx(0.5)  # User names ignore case.

    # The workspace (project input, work product) comes back as it was saved.
    restored = Workspace(**conversations[0]["workspace"])
    assert restored.project_notes == "Hotel, 40 rooms" and restored.document_title == "Checklist"


def test_saving_again_replaces_the_conversation_and_keeps_its_creation_date():
    user_store.save_conversation("sergi", _conversation("a", "First question", 0.01))
    created = user_store.load_conversations("sergi")[0]["created"]
    user_store.save_conversation("sergi", _conversation("a", "First question", 0.04))

    conversations = user_store.load_conversations("sergi")
    assert len(conversations) == 1
    assert conversations[0]["created"] == created
    assert user_store.total_cost("sergi") == pytest.approx(0.04)


def test_user_file_name_is_safe():
    user_store.save_conversation("../evil name", _conversation("a", "Question", 0.0))
    assert [path.name for path in settings.USERS_DIR.iterdir()] == ["___evil_name.json"]
