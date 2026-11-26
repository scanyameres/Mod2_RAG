"""Settings shared by all tests.

The GitHub backup of the histories (history_backup.py) is switched off, even if HISTORY_REPO
and GITHUB_TOKEN are in .env: the tests must not reach GitHub. load_dotenv() does not
override variables that are already set, so empty values keep the backup off.
"""

import pytest


@pytest.fixture(autouse=True)
def no_history_backup(monkeypatch):
    monkeypatch.setenv("HISTORY_REPO", "")
    monkeypatch.setenv("GITHUB_TOKEN", "")


@pytest.fixture(autouse=True)
def test_categories(monkeypatch):
    """The tests use their own categories (tests/categories.toml), not the real ones."""
    from pathlib import Path

    from scanya_ae_afa_updated0209_2_5 import settings

    monkeypatch.setattr(settings, "CATEGORIES_FILE", Path(__file__).parent / "categories.toml")
