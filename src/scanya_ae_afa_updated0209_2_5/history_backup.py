"""Copy of the user histories in a GitHub repository, so they survive a restart of the hosted app.

On Streamlit Community Cloud the app's disk is temporary: data/users/ is empty again after
every restart (a redeploy, or waking up after sleeping). This module keeps a copy of each
user's JSON file in a separate, private GitHub repository, through the GitHub REST API
("contents" endpoint). user_store.py calls it; no Streamlit code here.

Why a separate repository and not the app's own: a commit to the repository the app is
deployed from makes Streamlit restart the app, in the middle of other users' conversations.
A separate repository also lets the token have access to the histories only.

Configured by two environment variables (in .env locally, in the app's Secrets on Streamlit):
- HISTORY_REPO:  "owner/name" of the private repository, e.g. "scanyameres/rules-assistant-history";
- GITHUB_TOKEN:  a fine-grained token with "Contents: read and write" on that repository only.
Without them the backup is off and the histories stay on the local disk only (as before).

Public: is_enabled(), download(), upload().
"""

import base64
import os

import httpx
from dotenv import load_dotenv

API_URL = "https://api.github.com"
TIMEOUT_SECONDS = 15


def _config() -> tuple[str, str] | None:
    """(repository, token), or None if the backup is not configured."""
    load_dotenv()
    repo, token = os.environ.get("HISTORY_REPO", "").strip(), os.environ.get("GITHUB_TOKEN", "").strip()
    return (repo, token) if repo and token else None


def is_enabled() -> bool:
    """True if HISTORY_REPO and GITHUB_TOKEN are set."""
    return _config() is not None


def _request(method: str, path: str, raw: bool = False, **kwargs) -> httpx.Response:
    """One request to the contents endpoint of the history repository.

    raw=True asks for the file itself instead of a JSON description (which only includes the
    content for files below 1 MB; a long history can be larger).
    """
    repo, token = _config()
    accept = "application/vnd.github.raw+json" if raw else "application/vnd.github+json"
    headers = {"Authorization": f"Bearer {token}", "Accept": accept}
    return httpx.request(
        method, f"{API_URL}/repos/{repo}/contents/{path}", headers=headers, timeout=TIMEOUT_SECONDS, **kwargs
    )


def download(path: str) -> bytes | None:
    """Content of the file at `path` in the repository, or None if it does not exist.

    Raises:
        httpx.HTTPError: network problem, or another error than "not found" (e.g. bad token).
    """
    response = _request("GET", path, raw=True)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.content


def upload(path: str, data: bytes, message: str) -> None:
    """Create or replace the file at `path` in the repository with one commit.

    GitHub needs the id ("sha") of the version being replaced, so the file is looked up first.

    Raises:
        httpx.HTTPError: network problem, bad token, no write access ...
    """
    existing = _request("GET", path)
    if existing.status_code not in (200, 404):
        existing.raise_for_status()
    body = {"message": message, "content": base64.b64encode(data).decode("ascii")}
    if existing.status_code == 200:
        body["sha"] = existing.json()["sha"]
    _request("PUT", path, json=body).raise_for_status()
