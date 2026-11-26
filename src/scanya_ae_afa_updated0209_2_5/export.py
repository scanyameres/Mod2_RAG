"""Export of a conversation as Markdown, CSV or JSON (no Streamlit code).

All three take a conversation as page_chat.py builds it for the history (user_store.py):
a dict with "id", "title", "messages", "workspace", "settings" and "usage".

- Markdown: to read or to paste into a document: every question and answer, the references
  each answer cites, and the work product at the end. Labels in the user's language.
- CSV: one row per message (number, role, text, cited references), for Excel. The column
  names stay English, as in any data file. Written with a BOM, so Excel reads the accents.
- JSON: the complete conversation, also the search steps, settings and costs; the same
  format as the saved history.

Public: to_markdown(), to_csv(), to_json().
"""

import csv
import io
import json
from datetime import date

from scanya_ae_afa_updated0209_2_5 import translations
from scanya_ae_afa_updated0209_2_5.workspace import Workspace, citation_numbers, reference_list


def _cited_sources(message: dict) -> list[dict]:
    """The passages an assistant message cites, by number (none for a user message)."""
    numbers = citation_numbers(message["content"])
    cited = [source for source in message.get("sources", []) if source["number"] in numbers]
    return sorted(cited, key=lambda source: source["number"])


def to_markdown(conversation: dict, language: str = translations.DEFAULT_LANGUAGE) -> str:
    """The conversation as a Markdown text, with its work product at the end."""

    def text(key: str, **values) -> str:
        return translations.text(key, language, **values)

    parts = [
        f"# {text('conversation')}: {conversation['title']}",
        f"*{text('exported_on', date=date.today().isoformat())}*",
    ]
    for message in conversation["messages"]:
        speaker = text("you") if message["role"] == "user" else text("assistant")
        parts.append(f"## {speaker}\n\n{message['content']}")
        cited = _cited_sources(message)
        if cited:
            parts.append(f"**{text('references')}**\n\n{reference_list(cited, language)}")
    workspace = Workspace(**conversation["workspace"])
    if workspace.document:
        parts.append("---\n\n" + workspace.export_document(language))
    return "\n\n".join(parts) + "\n"


def to_csv(conversation: dict) -> bytes:
    """The conversation as CSV: one row per message. UTF-8 with BOM, for Excel."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["number", "role", "text", "references"])
    for number, message in enumerate(conversation["messages"], start=1):
        references = "; ".join(
            f"[{source['number']}] {source['source']}" + (f", p. {source['page']}" if source["page"] else "")
            for source in _cited_sources(message)
        )
        writer.writerow([number, message["role"], message["content"], references])
    return output.getvalue().encode("utf-8-sig")


def to_json(conversation: dict) -> str:
    """The complete conversation as JSON (the format of the saved history)."""
    return json.dumps(conversation, ensure_ascii=False, indent=1)
