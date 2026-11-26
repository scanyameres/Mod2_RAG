"""App-wide settings that the admin saves in the app (no Streamlit code).

Two kinds of values, all in one small JSON file (settings.APP_SETTINGS_FILE):
- defaults of the Settings section of the Assistant page: document types switched on, hybrid
  search, passages per search, searches per answer, model. Every new conversation starts with
  them; any user can change them for their own conversation, but only the admin can save them
  as the new defaults (Knowledge base page);
- app rules that only the admin can change: the spending limit per user and whether the guard
  (guard.py) checks the questions.

Without a saved file, the values come from settings.py. Saved values are checked when read
(unknown model, document type that no longer exists, number out of range), so a stale file
cannot break the app.

On the hosted app the disk is emptied at every restart, so the file is also copied to the
backup repository of the histories (history_backup.py), like a user's history.

Public: KEYS, load(), save().
"""

import json

from scanya_ae_afa_updated0209_2_5 import history_backup, settings
from scanya_ae_afa_updated0209_2_5.categories import load_categories

# Path of the copy in the backup repository.
BACKUP_PATH = "settings/app_settings.json"

# The keys of the dict returned by load() and accepted by save().
KEYS = ("active_categories", "hybrid", "top_k", "max_searches", "model_name", "guard_enabled", "spending_limit_usd")

# True once the backup was asked for the file in this server process, so a missing file is not
# looked for on GitHub at every page run.
_backup_checked = False


def _defaults() -> dict:
    """The values from settings.py, used for everything that was never saved."""
    return {
        "active_categories": [category.id for category in load_categories()],
        "hybrid": True,
        "top_k": settings.TOP_K,
        "max_searches": settings.MAX_SEARCHES,
        "model_name": settings.CHAT_MODELS[0],
        "guard_enabled": True,
        "spending_limit_usd": settings.SPENDING_LIMIT_USD,
    }


def _checked(values: dict) -> dict:
    """`values` over the defaults, with every value made valid (wrong ones fall back to the default)."""
    default = _defaults()
    result = {**default, **{key: values[key] for key in KEYS if key in values}}
    known_ids = default["active_categories"]
    result["active_categories"] = [cid for cid in result["active_categories"] if cid in known_ids]
    result["hybrid"] = bool(result["hybrid"])
    result["top_k"] = min(max(int(result["top_k"]), 1), settings.TOP_K_MAX)
    result["max_searches"] = min(max(int(result["max_searches"]), 1), settings.MAX_SEARCHES_MAX)
    if result["model_name"] not in settings.CHAT_MODELS:
        result["model_name"] = default["model_name"]
    result["guard_enabled"] = bool(result["guard_enabled"])
    result["spending_limit_usd"] = max(float(result["spending_limit_usd"]), 0.0)
    return result


def load() -> dict:
    """The current app settings (a dict with all KEYS)."""
    global _backup_checked
    path = settings.APP_SETTINGS_FILE
    if not path.exists() and history_backup.is_enabled() and not _backup_checked:
        _backup_checked = True
        try:
            data = history_backup.download(BACKUP_PATH)
        except Exception as error:  # Network problem: run with the defaults, do not stop the app.
            print(f"App settings not loaded from the backup: {error}")
            data = None
        if data is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    if not path.exists():
        return _checked({})
    return _checked(json.loads(path.read_text(encoding="utf-8")))


def save(values: dict) -> None:
    """Save `values` (all KEYS) as the new app settings, and copy them to the backup if it is on.

    Raises:
        httpx.HTTPError: the file was saved on this server, but the copy to GitHub failed.
    """
    path = settings.APP_SETTINGS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_checked(values), indent=1), encoding="utf-8")
    if history_backup.is_enabled():
        history_backup.upload(BACKUP_PATH, path.read_bytes(), "App settings")
