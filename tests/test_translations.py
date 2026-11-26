"""Tests of the interface languages (translations.py, language.py) and of the conversation export (export.py). Offline."""

import csv
import io
import json
import re
from pathlib import Path

import pytest

from scanya_ae_afa_updated0209_2_5 import export, flow_diagram, settings, translations
from scanya_ae_afa_updated0209_2_5.categories import load_categories

SOURCE_DIR = Path(translations.__file__).parent


def _placeholders(text: str) -> set[str]:
    return set(re.findall(r"\{(\w+)", text))


@pytest.mark.parametrize("key", list(translations.TEXTS))
def test_every_text_exists_in_every_language_with_the_same_placeholders(key):
    versions = translations.TEXTS[key]
    assert len(versions) == len(translations.LANGUAGES) and all(version.strip() for version in versions)
    assert len({frozenset(_placeholders(version)) for version in versions}) == 1, versions


def test_every_key_used_in_the_code_exists():
    """Every t("...") of the interface code names a text of translations.py (a typo would crash the page)."""
    used = set()
    for path in SOURCE_DIR.glob("*.py"):
        used |= set(re.findall(r"\bt\(\s*\"(\w+)\"", path.read_text(encoding="utf-8")))
        used |= set(re.findall(r"\bt\(\s*'(\w+)'", path.read_text(encoding="utf-8")))
    assert used, "No t() calls found."
    assert used <= set(translations.TEXTS), used - set(translations.TEXTS)


def test_text_fills_in_the_values_and_falls_back_to_english():
    assert translations.text("search_n", "de", number=2) == "Suche 2"
    assert translations.text("search_n", "xx", number=2) == "Search 2"


def test_flow_diagram_in_catalan():
    html = flow_diagram.diagram_html("search", language="ca")
    assert "<b>Base de coneixement" in html
    assert flow_diagram.stage_label("model", "de") == "Denkt nach…"


def test_real_categories_have_all_names(monkeypatch):
    monkeypatch.setattr(settings, "CATEGORIES_FILE", settings.PROJECT_ROOT / "categories.toml")
    for category in load_categories():
        for code in translations.LANGUAGES:
            assert category.label(code) and category.tooltip(code)
        assert category.label("ca") != category.name


def test_test_categories_fall_back_to_english():
    category = load_categories()[0]  # tests/categories.toml has no translations.
    assert category.label("de") == category.name


# --- Export ---

SOURCE = {"number": 1, "source": "building_code.txt", "section": "Art. 6", "page": 3}
CONVERSATION = {
    "id": "abc123",
    "title": "Abstandsfläche?",
    "messages": [
        {"role": "user", "content": "Abstandsfläche?"},
        {"role": "assistant", "content": "0,4 H, mindestens 3 m [1].", "steps": [], "sources": [SOURCE]},
    ],
    "workspace": {"document_title": "Checklist", "document": "- 3 m [1]", "sources": {"c1": SOURCE}},
    "settings": {"model_name": settings.CHAT_MODELS[0]},
    "usage": {},
}


def test_markdown_export_has_questions_answers_references_and_work_product():
    text = export.to_markdown(CONVERSATION, "ca")
    assert text.startswith("# Conversa: Abstandsfläche?")
    assert "## Tu\n\nAbstandsfläche?" in text and "## Assistent\n\n0,4 H, mindestens 3 m [1]." in text
    assert "- [1] building_code.txt, Art. 6, pàgina 3" in text
    assert "# Checklist" in text and "## Referències" in text


def test_csv_export_has_one_row_per_message():
    data = export.to_csv(CONVERSATION)
    assert data.startswith("﻿".encode("utf-8"))  # BOM, so Excel reads the accents.
    rows = list(csv.reader(io.StringIO(data.decode("utf-8-sig"))))
    assert rows[0] == ["number", "role", "text", "references"]
    assert rows[2] == ["2", "assistant", "0,4 H, mindestens 3 m [1].", "[1] building_code.txt, p. 3"]


def test_json_export_is_the_whole_conversation():
    assert json.loads(export.to_json(CONVERSATION)) == CONVERSATION
