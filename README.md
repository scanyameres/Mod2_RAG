# Building Rules Assistant (Sprint 2)

A chatbot that helps find the building regulations and standards that apply to a project, from documents in a knowledge base. Built with LangChain, OpenRouter, LanceDB and Streamlit.
Task description: [125.md](125.md).

- **Chat** about the rules for your project; every answer lists its references: document, section (e.g. "Art. 6 Abstandsflächen" or "4 Bäder › 4.2 Lüftung"), page and the exact passage.
- **Project input**: attach drafts, requirement lists or notes that describe the project.
- **Settings**: choose which document types are searched, switch hybrid search on or off, set how many passages the assistant gets per search, pick the model.
- **Output**: ask for a document (checklist, list of applicable rules, summary); it appears next to the chat, can be revised by chatting, and downloaded.
- **Search steps**: for every answer, see what the assistant searched for, all passages it was given and how well each one matched, and which ones the answer cites.
- **Hybrid search**: finds passages by meaning (embeddings) and by exact words (BM25), so both "minimum ceiling height in offices" and "DIN 4102-4" work.
- **Knowledge base page**: add or remove the documents the assistant searches, per document type.
- **Login and history** (optional): log in or create an account in the sidebar; your conversations and work products are then saved and can be reopened on the **My history** page.
- **Costs**: the sidebar shows the estimated cost of the chat so far, per model, and the total of the logged-in user.

**Status:** tested offline with fake models; not yet run with a real API key. See [TASKS.md](TASKS.md).

## Setup

1. Install the dependencies (creates `.venv`; uv downloads Python 3.14 if needed):

   ```bash
   uv sync
   ```

2. OpenRouter API key ([get one here](https://openrouter.ai/keys)). The app reads `OPENROUTER_API_KEY` the same way as the Sprint 1 project: from the environment, or from a `.env` file in the project root (copy `.env.example` to `.env` and fill it in; the file is git-ignored). If the key is already set as an environment variable, there is nothing to do.

## Run

Double-click `start_app.bat`, or:

```bash
uv run streamlit run src/scanya_ae_afa_updated0209_2_5/app.py
```

First open **Knowledge base** (top of the page), pick a document type and upload PDF / TXT / MD files. The list shows how many sections were recognised in each document; with 0, its references name the page only. Then go back to **Assistant** and ask. Scanned PDFs (images without text) are not supported.

Logging in is optional. A dummy account exists for now: user `sergi`, password `sergi123`. New accounts can be created in the sidebar; any password is accepted for now.

Without the app: after copying files into `data/library/<category id>/` or deleting some, run `build_index.bat` to bring the index up to date (new files are embedded, deleted ones dropped; unchanged ones are skipped). `build_index.bat --rebuild` embeds everything again. Both show the estimated cost and ask first.

To try the app without real documents, use the invented regulations in `sample_data/`: its [README](sample_data/README.md) says how to load them and which answers to expect.

`uv run` installs the dependencies by itself on the first start, so step 1 of the setup is optional.

Tests (no API key needed):

```bash
uv run pytest
```

## Project layout

| Path | Purpose |
|---|---|
| `src/scanya_ae_afa_updated0209_2_5/` | Application code (modules are described in `Architecture.md`). |
| `categories.toml` | The document types. Edit to rename, add or remove them. |
| `sample_data/<category id>/` | Invented sample regulations for testing (free to share), with expected answers in its README. |
| `data/library/<category id>/` | Knowledge-base documents. Git-ignored: may be copyrighted. |
| `data/index/` | Search index (LanceDB), built from the library. Git-ignored. |
| `data/users/` | History of the logged-in users, one JSON file each. Git-ignored: contains passages of the documents. |
| `config.yaml` | User accounts (hashed passwords) and the login-cookie key. Committed with a dummy account. |
| `tests/` | Offline tests. |
| `.streamlit/config.toml` | Streamlit theme and upload limit. |
| `.env.example` | Template for the API key. |
| `CLAUDE.md` | Working instructions for Claude Code. |

## Documentation

- [Architecture.md](Architecture.md): components, how they work together, and design decisions.
- [TASKS.md](TASKS.md): status of the core and optional tasks from `125.md`.
