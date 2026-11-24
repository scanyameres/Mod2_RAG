"""Per-user history of conversations, as JSON files (no Streamlit code, no API calls).

Adapted from the Sprint 1 project (scanya-AE.AFA.updated0209.1.6, user_store.py): there one
file per user held job profiles, here it holds conversations. No embeddings are needed.

Each logged-in user has one file, data/users/<username>.json:
    {"conversations": [conversation, ...]}

A conversation is a plain dict, built and read by page_chat.py:
- "id":        unique id of the conversation;
- "title":     its first question (shortened);
- "created", "updated": date and time, e.g. "2026-11-23T20:15:00";
- "messages":  the chat, as shown on the page (answers with their steps and sources);
- "workspace": project input, work product and numbered sources (the Workspace fields);
- "settings":  active document types, hybrid search on/off, chat model;
- "usage":     requests, tokens and cost per chat model (see pricing.py).

The files are in data/, which is git-ignored: a conversation contains passages of the
knowledge-base documents, which may be copyrighted.

Public: load_conversations(), save_conversation(), total_cost().
"""

import json
import re
from datetime import datetime
from pathlib import Path

from scanya_ae_afa_updated0209_2_5 import pricing, settings


def load_conversations(username: str) -> list[dict]:
    """All conversations of the user, last changed first ([] if the user has none yet)."""
    path = _user_file(username)
    if not path.exists():
        return []
    conversations = json.loads(path.read_text(encoding="utf-8"))["conversations"]
    return sorted(conversations, key=lambda conversation: conversation["updated"], reverse=True)


def save_conversation(username: str, conversation: dict) -> None:
    """Add the conversation to the user's file, or replace the stored one with the same "id".

    Sets "updated" to now, and "created" if the conversation is new.
    """
    now = datetime.now().isoformat(timespec="seconds")
    stored = load_conversations(username)
    earlier = next((other for other in stored if other["id"] == conversation["id"]), None)
    others = [other for other in stored if other["id"] != conversation["id"]]
    conversation = {**conversation, "created": earlier["created"] if earlier else now, "updated": now}
    path = _user_file(username)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"conversations": [conversation, *others]}, indent=1), encoding="utf-8")


def total_cost(username: str) -> float:
    """What the user spent so far, in USD: the cost of all saved conversations."""
    return sum(pricing.total_cost(conversation["usage"]) for conversation in load_conversations(username))


def _user_file(username: str) -> Path:
    """Path of the user's JSON file (username made safe for a file name)."""
    safe_name = re.sub(r"[^a-z0-9_-]", "_", username.casefold())
    return settings.USERS_DIR / f"{safe_name}.json"
