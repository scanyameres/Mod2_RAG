"""Tests of the backbone that run offline: no API key, no network.

The embedding model and the chat model are replaced by fakes from LangChain, and the data
folders by a temporary folder. Run with: uv run pytest
"""

import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from fakes import FakeGuardModel
from scanya_ae_afa_updated0209_2_5 import agent, chunking, config, library, retrieval, settings
from scanya_ae_afa_updated0209_2_5.categories import load_categories
from scanya_ae_afa_updated0209_2_5.embeddings import OpenRouterEmbeddings
from scanya_ae_afa_updated0209_2_5.workspace import Workspace, citation_numbers

# Fake embeddings: the same text always gives the same (meaningless) vector.
EMBEDDINGS = DeterministicFakeEmbedding(size=32)

BUILDING_CODE = (
    "Art. 6 Abstandsflächen\nDie Tiefe der Abstandsfläche beträgt 0,4 H, mindestens 3 m.\n\n"
    "Art. 28 Brandwände\nBrandwände müssen feuerbeständig sein und aus nichtbrennbaren Baustoffen bestehen."
)
WORKPLACE_RULES = "Arbeitsräume müssen eine lichte Höhe von mindestens 2,50 m haben."
FIRE_STANDARD = "DIN 4102-4 regelt die Klassifizierung von Baustoffen und Bauteilen nach ihrem Brandverhalten."


@pytest.fixture(autouse=True)
def temporary_data_folders(tmp_path, monkeypatch):
    """Point the library and the index to an empty temporary folder for every test."""
    monkeypatch.setattr(settings, "LIBRARY_DIR", tmp_path / "library")
    monkeypatch.setattr(settings, "INDEX_DIR", tmp_path / "index")


@pytest.fixture
def filled_library():
    """Three small documents in three categories."""
    library.add_document("building_code.txt", BUILDING_CODE.encode(), "general_building", EMBEDDINGS)
    library.add_document("workplaces.txt", WORKPLACE_RULES.encode(), "business", EMBEDDINGS)
    library.add_document("din_4102.txt", FIRE_STANDARD.encode(), "fire_safety", EMBEDDINGS)


def test_categories_file_is_valid():
    categories = load_categories()
    assert len(categories) >= 2
    assert len({category.id for category in categories}) == len(categories)


def test_split_pages_keeps_page_numbers(monkeypatch):
    monkeypatch.setattr(settings, "CHUNK_SIZE", 50)
    monkeypatch.setattr(settings, "CHUNK_OVERLAP", 10)
    chunks = chunking.split_pages([(1, "First page. " * 20), (2, "Second page. " * 20)])
    assert {chunk.page for chunk in chunks} == {1, 2}
    assert all(len(chunk.text) <= 50 for chunk in chunks)


LAW_PAGE_1 = """Bauordnung (Auszug)
Erster Teil
Allgemeine Vorschriften
Art. 1
Anwendungsbereich
(1) Dieses Gesetz gilt für alle baulichen Anlagen. Art. 6 Abs. 5
Satz 1 bleibt unberührt.
§ 14 Abs. 2 gilt entsprechend.
Zweiter Teil
Das Grundstück und seine Bebauung
Art. 6 Abstandsflächen, Abstände
(1) Die Tiefe der Abstandsfläche beträgt 0,4 H, mindestens 3 m.
"""
LAW_PAGE_2 = """(2) Abstandsflächen müssen auf dem Grundstück selbst liegen.
Art. 28
Brandwände
(1) Brandwände müssen feuerbeständig sein.
"""
STANDARD = """1 Anwendungsbereich
Diese Norm gilt für die Planung von Wohnungen.
2 Begriffe
Es gelten folgende Begriffe.
3 Stellplätze je Wohnung sind nachzuweisen, wenn die Satzung der Gemeinde dies verlangt
3 Sanitärräume
3.1 Allgemeines
Die lichte Höhe beträgt 2,50 m.
2.50 m Breite sind einzuhalten.
1 Wohnzimmer 20 m²
3.2 Lüftung
3.2.1 Fensterlose Bäder müssen eine wirksame Lüftung haben.
"""


def _sections(pages):
    """The section of every chunk, keyed by the first line of the chunk's body."""
    return [(chunk.page, chunk.section) for chunk in chunking.split_pages(pages)]


def test_sections_of_a_law():
    part_1, part_2 = "Erster Teil Allgemeine Vorschriften", "Zweiter Teil Das Grundstück und seine Bebauung"
    assert _sections([(1, LAW_PAGE_1), (2, LAW_PAGE_2)]) == [
        (1, ""),  # The title line, before any heading.
        (1, f"{part_1} › Art. 1 Anwendungsbereich"),  # "Art. 6 Abs. 5" and "§ 14 Abs. 2" are no headings.
        (1, f"{part_2} › Art. 6 Abstandsflächen, Abstände"),
        (2, f"{part_2} › Art. 6 Abstandsflächen, Abstände"),  # The section continues on the next page.
        (2, f"{part_2} › Art. 28 Brandwände"),
    ]


def test_sections_of_a_numbered_standard():
    chunks = chunking.split_pages([(None, STANDARD)])
    assert [chunk.section for chunk in chunks] == [
        "1 Anwendungsbereich",
        "2 Begriffe",
        "3 Sanitärräume › 3.1 Allgemeines",
        "3 Sanitärräume › 3.2 Lüftung",
    ]
    # Sentences and table rows that start with a number stay ordinary text.
    assert "3 Stellplätze je Wohnung" in chunks[1].text
    assert "2.50 m Breite" in chunks[2].text and "1 Wohnzimmer 20 m²" in chunks[2].text
    assert "3.2.1 Fensterlose Bäder" in chunks[3].text


def test_sections_of_markdown_and_of_plain_text():
    markdown = "# Vorgaben\nEinleitung.\n## Bäder\n### Lüftung\nJedes Bad braucht einen Ventilator.\n## Küchen\nText."
    assert [chunk.section for chunk in chunking.split_pages([(None, markdown)])] == [
        "Vorgaben",
        "Vorgaben › Bäder › Lüftung",
        "Vorgaben › Küchen",
    ]
    assert [chunk.section for chunk in chunking.split_pages([(None, WORKPLACE_RULES)])] == [""]


def test_section_is_stored_searched_and_reported(monkeypatch):
    monkeypatch.setattr(settings, "CHUNK_SIZE", 120)
    monkeypatch.setattr(settings, "CHUNK_OVERLAP", 0)
    body = "\n".join(f"Absatz {n}: Der Luftwechsel muss mindestens {n * 10} Kubikmeter je Stunde betragen." for n in range(1, 6))
    library.add_document("Wohnungsnorm.txt", f"4 Bäder\n4.2 Lüftung\n{body}".encode(), "housing", EMBEDDINGS)

    document = library.list_documents()[0]
    assert document["chunks"] > 2 and document["sections"] == 1

    # "Bäder" stands only in the heading, yet every chunk of the section is found by that word.
    hits = retrieval.search("Bäder", ["housing"], k=20, embeddings=EMBEDDINGS)
    by_keyword = [hit for hit in hits if hit.keyword_rank]
    assert len(by_keyword) == document["chunks"]
    assert all(hit.section == "4 Bäder › 4.2 Lüftung" for hit in hits)
    assert any("Bäder" not in hit.text for hit in by_keyword)  # The passage text itself is unchanged.

    source = Workspace().add_source(hits[0])
    assert agent._location(source, {"housing": "Housing"}) == '[1] Wohnungsnorm.txt, section "4 Bäder › 4.2 Lüftung" (Housing)'


def test_reciprocal_rank_fusion_prefers_items_in_both_rankings():
    scores = retrieval.reciprocal_rank_fusion([["a", "b", "c"], ["c", "a", "d"]])
    assert max(scores, key=scores.get) == "a"  # Rank 1 and 2 beats rank 3 and 1.
    assert scores["a"] == pytest.approx(1 / 61 + 1 / 62)
    assert scores["d"] == pytest.approx(1 / 63)  # Found by one search only.


def test_keyword_side_finds_exact_reference(filled_library):
    all_ids = [category.id for category in load_categories()]
    hits = retrieval.search("DIN 4102-4", all_ids, embeddings=EMBEDDINGS)
    by_keyword = [hit for hit in hits if hit.keyword_rank == 1]
    assert by_keyword and by_keyword[0].source == "din_4102.txt"


def test_switched_off_category_is_not_searched(filled_library):
    hits = retrieval.search("DIN 4102-4 lichte Höhe", ["general_building", "business"], embeddings=EMBEDDINGS)
    assert hits
    assert {hit.category for hit in hits} <= {"general_building", "business"}
    assert retrieval.search("DIN 4102-4", [], embeddings=EMBEDDINGS) == []


def test_hybrid_switched_off_uses_the_vector_search_only(filled_library):
    all_ids = [category.id for category in load_categories()]
    hits = retrieval.search("DIN 4102-4", all_ids, hybrid=False, embeddings=EMBEDDINGS)
    assert hits
    assert all(hit.keyword_rank is None and hit.vector_rank is not None for hit in hits)
    assert [hit.vector_rank for hit in hits] == sorted(hit.vector_rank for hit in hits)


def test_add_replace_and_remove_document(filled_library):
    assert len(library.list_documents()) == 3
    # Same name, same category: replaces the old version instead of adding a second one.
    library.add_document("workplaces.txt", b"Neue Fassung: mindestens 2,75 m.", "business", EMBEDDINGS)
    documents = library.list_documents()
    assert len(documents) == 3
    assert (settings.LIBRARY_DIR / "business" / "workplaces.txt").read_bytes().startswith(b"Neue Fassung")

    workplace = next(document for document in documents if document["source"] == "workplaces.txt")
    library.remove_document(workplace["doc_id"])
    assert len(library.list_documents()) == 2
    assert not (settings.LIBRARY_DIR / "business" / "workplaces.txt").exists()
    assert retrieval.search("lichte Höhe", ["business"], embeddings=EMBEDDINGS) == []


def test_rebuild_index_from_library_files(filled_library):
    indexed, problems = library.rebuild_index(EMBEDDINGS)
    assert (indexed, problems) == (3, [])
    assert len(library.list_documents()) == 3


def test_bad_uploads_are_rejected():
    with pytest.raises(ValueError, match="Unknown category"):
        library.add_document("a.txt", b"text", "no_such_category", EMBEDDINGS)
    with pytest.raises(ValueError, match="Unsupported file type"):
        library.add_document("a.exe", b"text", "business", EMBEDDINGS)
    with pytest.raises(ValueError, match="No text found"):
        library.add_document("empty.txt", b"   ", "business", EMBEDDINGS)
    assert library.list_documents() == []


def test_validate_question():
    assert agent.validate_question("What is the minimum distance?") is None
    assert agent.validate_question("   ")
    assert agent.validate_question("x" * (settings.MAX_QUESTION_LENGTH + 1))


def test_embeddings_wrapper_batches_and_keeps_order(monkeypatch):
    """OpenRouterEmbeddings calls the SDK client from config.get_client() in batches."""
    requests = []

    class FakeEmbeddingsApi:
        def create(self, model, input):
            requests.append((model, list(input)))
            # Answer in reverse order, as an API may: the wrapper must sort by index.
            items = [type("Item", (), {"index": i, "embedding": [float(len(text))]}) for i, text in enumerate(input)]
            return type("Response", (), {"data": items[::-1]})

    monkeypatch.setattr(config, "get_client", lambda provider: type("Client", (), {"embeddings": FakeEmbeddingsApi()}))
    monkeypatch.setattr(settings, "EMBEDDING_BATCH_SIZE", 2)
    vectors = OpenRouterEmbeddings().embed_documents(["a", "bb", "ccc"])
    assert vectors == [[1.0], [2.0], [3.0]]
    assert [len(batch) for _, batch in requests] == [2, 1]
    assert requests[0][0] == settings.EMBEDDING_MODEL


def test_citation_numbers():
    assert citation_numbers("Rule A [2]. Rule B [1][2] and [3, 5]. Not a citation: [x] or 4.") == [2, 1, 3, 5]


def test_workspace_project_input(monkeypatch):
    workspace = Workspace()
    assert workspace.project_input() == ""
    workspace.project_notes = "Hotel, 40 rooms"
    workspace.add_project_file("draft.txt", b"Four storeys, restaurant on the ground floor.")
    text = workspace.project_input()
    assert "Hotel, 40 rooms" in text and "File: draft.txt" in text and "Four storeys" in text
    assert not workspace.project_input_is_cut()
    with pytest.raises(ValueError, match="Unsupported file type"):
        workspace.add_project_file("plan.dwg", b"...")

    monkeypatch.setattr(settings, "MAX_PROJECT_INPUT_CHARS", 20)
    assert workspace.project_input_is_cut()
    assert workspace.project_input().endswith("too long]")


class FakeToolCallingModel(GenericFakeChatModel):
    """Fake chat model that replays prepared messages. Tools are accepted and ignored."""

    def bind_tools(self, tools, **kwargs):
        return self


def _run_agent(workspace, question, replies, categories=("general_building",)):
    """Run answer_question() with a fake model that gives `replies` one after the other."""
    return list(
        agent.answer_question(
            question,
            history=[],
            workspace=workspace,
            active_category_ids=list(categories),
            chat_model=FakeToolCallingModel(messages=iter(replies)), guard_model=FakeGuardModel(),
            embeddings=EMBEDDINGS,
        )
    )


def _search_call(query):
    return AIMessage(content="", tool_calls=[{"name": "search_documentation", "args": {"query": query}, "id": "call_1"}])


def test_agent_searches_then_answers(filled_library):
    workspace = Workspace()
    events = _run_agent(
        workspace,
        "Wie tief ist die Abstandsfläche?",
        [_search_call("Abstandsfläche Tiefe"), AIMessage(content="0,4 H, mindestens 3 m [1].")],
    )
    assert [event.kind for event in events] == ["tool_call", "tool_result", "answer"]
    assert events[0].text == "Abstandsfläche Tiefe"
    sources = events[1].sources
    assert sources and sources[0]["number"] == 1
    assert {source["category"] for source in sources} == {"general_building"}
    assert '[1] building_code.txt, section "Art. 6 Abstandsflächen" (General building rules)' in events[1].text
    assert events[2].text == "0,4 H, mindestens 3 m [1]."
    assert len(workspace.sources) == len(sources)


def test_passage_numbers_stay_the_same_across_answers(filled_library):
    workspace = Workspace()
    first = _run_agent(workspace, "Abstandsfläche?", [_search_call("Abstandsfläche"), AIMessage(content="[1]")])
    numbers_first = {source["chunk_id"]: source["number"] for source in first[1].sources}
    # A second answer in the same conversation, now also searching another document type.
    second = _run_agent(
        workspace,
        "Und DIN 4102-4?",
        [_search_call("DIN 4102-4 Abstandsfläche"), AIMessage(content="[1][3]")],
        categories=("general_building", "fire_safety"),
    )
    numbers_second = {source["chunk_id"]: source["number"] for source in second[1].sources}
    for chunk_id, number in numbers_first.items():
        assert numbers_second.get(chunk_id, number) == number  # Found again = same number.
    assert len(set(numbers_second.values())) == len(numbers_second)  # No number is used twice.
    assert max(numbers_second.values()) == len(workspace.sources)


def test_agent_writes_the_work_product(filled_library):
    workspace = Workspace()
    write_call = AIMessage(
        content="",
        tool_calls=[{"name": "write_document", "args": {"title": "Checklist", "content": "## Distances\n\n- 0,4 H, mindestens 3 m [1]."}, "id": "call_2"}],
    )
    events = _run_agent(workspace, "Write a checklist.", [_search_call("Abstandsfläche"), write_call, AIMessage(content="Done.")])
    assert [event.kind for event in events] == ["tool_call", "tool_result", "tool_call", "tool_result", "answer"]
    assert events[2].tool == "write_document" and events[2].text == "Checklist"
    assert workspace.document_title == "Checklist"
    assert workspace.document.startswith("## Distances")
    exported = workspace.export_document()
    assert exported.startswith("# Checklist")
    assert "## References" in exported and "- [1] building_code.txt, Art. 6 Abstandsflächen" in exported


def test_system_prompt_contains_the_conversation_state(filled_library):
    workspace = Workspace(project_notes="Hotel with 40 rooms", document_title="Checklist", document="- Rule [1]")
    _run_agent(workspace, "Abstandsfläche?", [_search_call("Abstandsfläche"), AIMessage(content="[1]")])
    categories = load_categories()
    prompt = agent._system_prompt(workspace, categories, ["general_building"])
    assert "Hotel with 40 rooms" in prompt
    assert "Title: Checklist" in prompt
    assert '[1] building_code.txt, section "Art. 6 Abstandsflächen" (General building rules)' in prompt
    active, inactive = prompt.split("Switched-off document types")
    assert "- General building rules" in active and "- Fire safety" in inactive


def test_hits_carry_the_match_values_of_both_searches(filled_library):
    all_ids = [category.id for category in load_categories()]
    hits = retrieval.search("DIN 4102-4", all_ids, embeddings=EMBEDDINGS)
    for hit in hits:
        # A value exists exactly when that search found the passage.
        assert (hit.similarity is None) == (hit.vector_rank is None)
        assert (hit.keyword_score is None) == (hit.keyword_rank is None)
    best = next(hit for hit in hits if hit.keyword_rank == 1)
    assert best.keyword_score > 0
    assert all(hit.similarity <= 1 for hit in hits if hit.similarity is not None)
    # The values travel with the passage to the page (References tab, Search steps tab).
    source = Workspace().add_source(best)
    assert source["keyword_score"] == best.keyword_score and source["similarity"] == best.similarity


def test_agent_gives_the_model_top_k_passages_per_search(filled_library):
    all_ids = [category.id for category in load_categories()]
    replies = [_search_call("Abstandsfläche Brandwände DIN lichte Höhe"), AIMessage(content="[1]")]
    events = list(
        agent.answer_question(
            "Frage", [], Workspace(), all_ids, top_k=2,
            chat_model=FakeToolCallingModel(messages=iter(replies)), guard_model=FakeGuardModel(), embeddings=EMBEDDINGS,
        )
    )
    result = next(event for event in events if event.kind == "tool_result")
    assert len(result.sources) == 2
    assert result.text.count("\n\n") == 1  # Two passages in the text the model reads.


def test_chat_model_is_created_with_the_temperature_from_settings(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    model = config.get_chat_model(settings.CHAT_MODELS[0], settings.TEMPERATURE)
    assert model.temperature == settings.TEMPERATURE == 0
