# Building Rules Assistant (Sprint 2)

A chatbot that helps find the building regulations and standards that apply to a project, from documents in a knowledge base. Built with LangChain, OpenRouter, LanceDB and Streamlit.
Task description: [docs/125.md](docs/125.md).

- **Chat** about the rules for your project; every answer lists its references: document, section (e.g. "Art. 6 Abstandsflächen" or "4 Bäder › 4.2 Lüftung"), page and the exact passage.
- **Project input**: attach drafts, requirement lists or notes that describe the project.
- **Settings**: choose which document types are searched, switch hybrid search on or off, set how many passages the assistant gets per search, pick the model.
- **Output**: ask for a document (checklist, list of applicable rules, summary); it appears next to the chat, can be revised by chatting, and downloaded.
- **Search steps**: for every answer, see what the assistant searched for, all passages it was given and how well each one matched, and which ones the answer cites.
- **Hybrid search**: finds passages by meaning (embeddings) and by exact words (BM25), so both "minimum ceiling height in offices" and "DIN 4102-4" work.
- **Knowledge base page**: everyone sees the documents the assistant searches; the admin also adds or removes them, rebuilds the index and sets the app settings (defaults of the Settings section, spending limit, safety check) for everyone.
- **Login and history** (optional): log in or create an account in the sidebar; your conversations and work products are then saved and can be reopened on the **My history** page.
- **Safety check**: a small, cheap model checks every question first; attempts to change the assistant's rules, off-topic and harmful requests are refused before the main model is called.
- **Costs**: the sidebar shows the estimated cost of the chat so far, per model, and the total of the logged-in user.

**Status:** tested offline with fake models; not yet run with a real API key. See [docs/TASKS.md](docs/TASKS.md).

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

The knowledge base comes ready with the invented sample regulations of `sample_data/` (13 documents, already indexed in `data/index/`). To add your own (admin only), open **Knowledge base** (top of the page), pick a document type and upload PDF / TXT / MD files. The list shows how many sections were recognised in each document; with 0, its references name the page only. Then go back to **Assistant** and ask. Scanned PDFs (images without text) are not supported.

Logging in is optional. Demo accounts (user / password): `lluis` / `lluis123`, `turing` / `turing123`, `guest` / `guest123`. They are in `config.yaml`, so they survive restarts of the hosted app. New accounts can be created in the sidebar; any password is accepted for now.

Admin: the account `sergi` has the role `admin` in `config.yaml` (no account created in the app gets a role). Its password is private; to change it, run `uv run python -m scanya_ae_afa_updated0209_2_5.set_password sergi`, then commit and push `config.yaml`.

Without the app: after copying files into `data/library/<category id>/` or deleting some, run `build_index.bat` to bring the index up to date (new files are embedded, deleted ones dropped; unchanged ones are skipped). `build_index.bat --rebuild` embeds everything again. Both show the estimated cost and ask first.

To try the app without real documents, use the invented regulations in `sample_data/`: its [README](sample_data/README.md) says how to load them and which answers to expect.

`uv run` installs the dependencies by itself on the first start, so step 1 of the setup is optional.

Tests (no API key needed):

```bash
uv run pytest
```

## Host on Streamlit Community Cloud

The free hosting of Streamlit runs the app on its servers; your computer can be off.

1. **History repository.** Create a new **private** GitHub repository for the user histories, e.g. `rules-assistant-history` (an empty one with a README is fine). It must not be the repository of the app: every commit to that one restarts the app.
2. **Token.** GitHub > Settings > Developer settings > Fine-grained tokens > Generate new token: *Repository access*: only the history repository; *Permissions*: Contents = Read and write.
3. **Login secret.** Make a new random key for the login cookie: `uv run python -c "import secrets; print(secrets.token_hex(32))"`. It goes into the Secrets below as `AUTH_COOKIE_KEY`. Locally, put one into `.env` as well (see `.env.example`), or logins are forgotten whenever the app restarts.
4. **Deploy.** At [share.streamlit.io](https://share.streamlit.io), *Create app* > from your GitHub repository of the app, branch `main`, main file `src/scanya_ae_afa_updated0209_2_5/app.py`. In *Advanced settings*: Python version **3.14** (it cannot be changed later without deleting the app), and in *Secrets* the content of `.streamlit/secrets.toml.example`, filled in.
5. **API key limit.** At [openrouter.ai/keys](https://openrouter.ai/keys), give the key a credit limit. The app stops each user at $1 (`settings.SPENDING_LIMIT_USD`), but a user who is not logged in can start over by reloading the page.
6. **Sharing.** In the app's *Share* settings, keep it private and invite your testers by e-mail, or make it public.

What to know about the hosted app:

- The dependencies come from `uv.lock`; Streamlit installs them on every deploy.
- Every push to `main` restarts the app. Its disk is temporary: the history survives (backed up to the history repository), but documents added in the Knowledge base page of the hosted app and accounts created there are lost at the next restart. To change the base library, add the files locally, run `build_index.bat` and push `data/library/` and `data/index/`.
- After 12 hours without visitors the app sleeps; the next visitor wakes it up (about a minute).

## Project layout

| Path | Purpose |
|---|---|
| `src/scanya_ae_afa_updated0209_2_5/` | Application code (modules are described in `docs/Architecture.md`). |
| `categories.toml` | The document types. Edit to rename, add or remove them. |
| `sample_data/<category id>/` | Invented sample regulations for testing (free to share), with expected answers in its README. |
| `data/library/<category id>/` | Knowledge-base documents. Committed, so the hosted app has them: only add documents that may be shared, never copyrighted ones (e.g. DIN standards). |
| `data/index/` | Search index (LanceDB), built from the library. Committed. |
| `data/users/` | History of the logged-in users, one JSON file each. Git-ignored (contains passages of the documents); the hosted app backs it up to a private repository. |
| `config.yaml` | User accounts (hashed passwords), name and lifetime of the login cookie. Committed with the demo accounts. |
| `tests/` | Offline tests. |
| `.streamlit/config.toml` | Streamlit theme and upload limit. |
| `.env.example` | Template for the API key (and the optional history backup). |
| `.streamlit/secrets.toml.example` | Template for the Secrets of the hosted app. |
| `docs/` | Task description (`125.md`), architecture, task status and diagrams (`Schema.png`, `model_costs.png`). |
| `CLAUDE.md` | Working instructions for Claude Code. |

## Documentation

- [docs/Architecture.md](docs/Architecture.md): components, how they work together, and design decisions.
- [docs/TASKS.md](docs/TASKS.md): status of the core and optional tasks from [docs/125.md](docs/125.md) (the task description).
