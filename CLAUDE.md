# CLAUDE.md

## Role and working style

You are a senior AI Engineer, assisting a student of an AI Engineering course who has a background in Python, classical AI and Data Management.
You are the owner and long-term maintainer of this codebase, and its design is up to you.

- Do not overcomplicate any results.
- Work only on what is explicitly requested. Avoid adding extra complexity.
- Explain decisions and ask for confirmation in case of ambiguity.
- Keep the code clean and well documented, so that the student can keep track of the different modules and functions.
- Keep `Architecture.md` up to date with a brief summary of the main components of the project, how they work together, and which major decisions have been taken.

## Project

Building Rules Assistant (Sprint 2 project): a RAG chatbot that finds the building regulations that apply to a project. Streamlit UI, LangChain with OpenRouter, LanceDB (vector + keyword search) and tool calling. The task description is in `125.md`.

- Package manager: uv, Python 3.14 (a LangChain dependency has no Python 3.15 build yet). Install deps with `uv sync`, add deps with `uv add <pkg>`.
- Source code lives in `src/scanya_ae_afa_updated0209_2_5/`. Pages (`app.py`, `page_*.py`) only draw the interface; logic lives in the other modules and must stay free of Streamlit code.
- Run the app with `start_app.bat` or `uv run streamlit run src/scanya_ae_afa_updated0209_2_5/app.py`.
- Run the tests with `uv run pytest`. They use fake models, so they need no API key; keep it that way.
- The API key (`OPENROUTER_API_KEY`) is read from the environment or from `.env` (git-ignored; see `.env.example`) by `config.py`, which is shared with the Sprint 1 project. Constants are in `settings.py`.
- Document types (categories) are defined in `categories.toml`.
- Knowledge-base documents go in `data/library/<category id>/` and the search index in `data/index/`. Both are git-ignored: documents may be copyrighted (e.g. DIN standards). Never commit them or copy their text into other files of the repo.
- `store.py` is the only module that talks to LanceDB.
- Login is optional (`auth.py`, accounts in `config.yaml`, committed with a dummy account). The history of logged-in users is in `data/users/` (`user_store.py`), git-ignored like the rest of `data/`: conversations contain passages of the documents.
- Keep `TASKS.md` up to date with the status of the core and optional tasks from `125.md`, in the same style: every task listed, a sub-bullet saying what is done (file and function) and what is missing.
