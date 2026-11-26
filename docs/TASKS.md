# Tasks Tracker

Core and optional tasks from `125.md`. Bonus points need **at least 2 Medium and 1 Hard** optional tasks.

Legend: `[x]` done · `[~]` partially done · `[ ]` not started

Summary (2026-11-26): all core tasks done. Optional: Easy 3 of 4 (the fourth partly), Medium 8 of 10, Hard 2 of 7, so the bonus rule is met.

## Core

### 1. RAG implementation

- [x] 1.1 Create a knowledge base relevant to the domain.
  - 16 public regulation PDFs in `data/library/<category id>/`: 13 national (CTE Documentos Básicos, RITE, RSCIEI), 2 Catalan (Codi d'Accessibilitat, Decret d'Habitabilitat), 1 municipal (POUM Terrassa). Indexed in LanceDB (`data/index/`, `store.py`) with the build tool (`build_index.py`, `library.sync_index()`); both folders are committed, so the hosted app starts with them. The admin can also add or remove documents on the Knowledge base page (`page_library.py` → `library.add_document()`).
- [x] 1.2 Implement standard document retrieval with embeddings.
  - Chunks and queries are embedded with `openai/text-embedding-3-small` (`embeddings.py`, through `config.get_client()`); `store.vector_search()` returns the nearest chunks by cosine distance. Used with the real key since 2026-11-24; tested offline with a fake embedding model.
- [x] 1.3 Use chunking strategies and similarity search.
  - `chunking.split_pages()`: the text is cut at recognised headings first, then by `RecursiveCharacterTextSplitter` (1,000 characters with 150 overlap, `settings.py`), never across pages. Every chunk has an exact page number and section. Similarity search: see 1.2.
- [x] 1.4 Advanced RAG: query translation and structured retrieval (from the task description).
  - Structured retrieval: every chunk stores its category, and both searches filter on the categories switched on in the sidebar (`store._category_filter()`). Every chunk also stores its section, the headings above it (`chunking._SectionTracker`); it is searched together with the passage and shown in every reference. On the real documents sections were found in all 16 (e.g. 636 in the Codi d'Accessibilitat), but only 11 and 4 in RITE and RSCIEI, whose references mostly name the page only.
  - Query translation: the agent writes its own search query from the conversation (a follow-up like "and for hotels?" becomes a full query), and is told to search in the documents' language and to retry with the regulation's terms (`prompts.SYSTEM_PROMPT`). Possible improvement: a dedicated rewrite step before the search.

### 2. Tool calling

- [x] 2.1 Implement at least 3 different tool calls.
  - 3 tools in `agent.py`, given to a LangChain agent (`create_agent()`): `search_documentation(query)` searches the active document types (at most `max_searches` times per answer); `read_passages(numbers)` gives back the text of passages found earlier in the conversation, so follow-up questions need no new search; `write_document(title, content)` creates or replaces the work product shown in the Output section.
- [x] 2.2 Functions are relevant to the domain (e.g. data analysis, calculations, API integrations).
  - Regulation search, re-reading the cited passages of a regulation, and writing a rules document for the project (checklist, list of applicable rules).

### 3. Domain specialisation

- [x] 3.1 Choose a specific domain or use case.
  - Architecture and building regulations: find the rules that apply to a building project in Catalonia (Spain).
- [x] 3.2 Create a focused knowledge base.
  - Three document types in `categories.toml` (`cte`, `gencat`, `poum_terrassa`: national, regional, municipal), switchable per conversation; see 1.1. The 13 invented sample documents used by the tests stay in `sample_data/`, with their six types in `tests/categories.toml`.
- [x] 3.3 Implement domain-specific prompts and responses.
  - `prompts.SYSTEM_PROMPT`: answer only from the documents, quote values and article references exactly, cite passages as `[n]`, name document and page when asked for the origin, use the project input, write documents with the tool, "not legal advice" note.
- [x] 3.4 Add relevant security measures for the domain.
  - LLM guard against prompt injection, off-topic and harmful requests before every answer (`guard.check_question()`, see Medium 3); admin role: only the admin changes the knowledge base and the app settings (`auth.is_admin()`, see Medium 4); spending limit per user (Medium 9); question length limit (`agent.validate_question()`); upload limits on type, size and file name (`library.py`, `workspace.py`); category and document ids validated before use in database filters (`categories.py`, `store.py`); search results, project input and work product are declared material, never instructions (`prompts.py`); login cookie signed with a secret from the environment (`auth._cookie_key()`).

### 4. Technical implementation

- [x] 4.1 Use LangChain with OpenRouter (OpenAI-compatible SDK) for LLM integration.
  - `create_agent()` with `@tool` functions (`agent.py`), chat model from `init_chat_model(..., model_provider="openrouter")` (`config.get_chat_model()`), embeddings through the OpenAI SDK pointed at OpenRouter (`config.get_client()`, taken from the Sprint 1 project). Used with the real key; tested offline with a fake chat model.
- [x] 4.2 Implement proper error handling.
  - API and model errors are caught in `page_chat._answer()` and shown with `st.error` (a missing API key gets its own message); the question can be asked again. Bad files are reported per file (`ValueError` from `chunking.read_pages()`); one bad file does not stop an upload or a rebuild. A failed GitHub backup is a warning, not a crash (`user_store.BackupError`). The guard fails closed.
- [x] 4.3 Include user input validation.
  - Question: not empty, at most 2,000 characters. Files: PDF / TXT / MD, at most 25 MB, must contain text. Project input: capped at 30,000 characters with a warning. Category: must exist in `categories.toml`. Saved app settings: clamped to valid values (`app_settings.checked()`).

### 5. User interface

- [x] 5.1 Create an intuitive interface using Streamlit or Next.js.
  - Streamlit, three pages (Assistant, Knowledge base, My history), in English, Catalan or German (Hard 4). Assistant page (`page_chat.py`) in three areas filling the window: sidebar with Project input and Documents to search; centre with the Chat, the question field, the per-chat settings (model, passages, searches) and the cost line; right with the Output (work product, references or search steps, switched with buttons below the box that get a green dot when a view has new content) and a flow diagram of the answer steps (`flow_diagram.py`; the running step pulses, its colours mark which controls and views belong to which step).
- [x] 5.2 Show relevant context and sources.
  - Below each answer: the cited passages with document, section, page, document type, how they were found, and the exact text. Output section: References view with every passage of the conversation; Search steps view with all passages the model was given for each search, best first, with their match values (`page_chat._passage_list()`).
- [x] 5.3 Display tool call results.
  - "Steps" box of each answer: every search with its query and the passages found, every re-read and every write of the work product. The Search steps view shows the same per answer in full (`page_chat._show_search_steps()`). The work product itself is shown in the Output section.
- [x] 5.4 Include progress indicators for long operations.
  - `st.status` box while an answer is generated, listing each step live and naming the running stage ("Checking the question…", "Reading the knowledge base…"); the flow diagram pulses on the running step; per-file progress while documents are indexed; spinner for the index rebuild.

## Easy

- [x] 1. Add conversation history and export functionality.
  - History: the conversation is kept for the session and sent to the model (last 12 messages); for a logged-in user every conversation is saved and can be reopened and continued from the My history page (`user_store.py`, `page_history.py`, `page_chat.open_conversation()`), backed up to a private GitHub repository on the hosted app (`history_backup.py`). Export: *Export* button above the chat (`page_chat._export_menu()`, `export.py`): Markdown, CSV, JSON; the work product alone can be downloaded as Markdown (`Workspace.export_document()`).
- [x] 2. Add visualisation of RAG process.
  - Search steps view (`page_chat._search_steps_tab()`): for each answer the path of the agent (Question → Search 1 → Search 2 → Answer), the settings used, and for every search the passages given to the model with two bars each: similarity by meaning and keyword score (`retrieval.Hit.similarity`, `keyword_score`), and a mark on the passages the answer cites. Flow diagram of the answer steps (`flow_diagram.py`), animated while an answer runs.
- [x] 3. Include source citations in responses.
  - `[n]` citations in answers and in the work product; numbers stay fixed for the whole conversation (`Workspace.add_source()`).
- [~] 4. Add an interactive help feature or chatbot guide.
  - Done: example questions in an empty chat, a "?" help text on every setting, explanations in the empty output views. Missing: a guide (e.g. a "How to use" box or clickable example questions).

## Medium

- [x] 1. Implement multi-model support (OpenAI, Anthropic, etc.).
  - "Model" select box below the question field, options from `settings.CHAT_MODELS` (two OpenAI models, one Anthropic), each with the estimated cost of a typical answer, passed to `config.get_chat_model()`; the model can be changed within a conversation, costs are kept per model. The guard always uses the cheapest model.
- [x] 2. Add real-time data updates to knowledge base.
  - Uploading or removing a document on the Knowledge base page (admin) changes the index at once, so the next question already searches it (`library.add_document()`, `library.remove_document()`). On the hosted app such changes last until the next restart; permanent changes go through `data/library/` and `build_index.bat`.
- [x] 3. Protect your app against prompt injection.
  - `guard.check_question()`: before every answer, a small model (`settings.GUARD_MODEL`, gpt-6-luna) judges the question with structured output (`GuardVerdict`) and blocks prompt injection, off-topic and harmful requests; only allowed questions reach the chosen chat model (`agent.answer_question()`, `blocked` event; warning in `page_chat._answer()`, with the reason in the interface language). It sees the start of the last answer, so follow-ups pass. Fails closed. Its cost is counted. The admin can switch it off for tests. Tested offline (`tests/test_guard.py`) and with the real model on 2026-11-25: 5 legitimate questions (incl. follow-up, greeting, German) allowed, 7 attacks or off-topic requests blocked. Second layer: the system prompt treats search results, project input and work product as material, never instructions (Core 3.4). Not covered by the guard: injected text inside project files or knowledge-base documents.
- [x] 4. Add user authentication and personalisation.
  - Optional login with `streamlit-authenticator` in the sidebar (`auth.login_area()`): log in, create an account, log out, remembered by a cookie signed with `AUTH_COOKIE_KEY`; accounts in `config.yaml` with hashed passwords, demo accounts `lluis`, `turing`, `guest`; `sergi` is the admin (`roles: [admin]`, `auth.is_admin()`, own password via `set_password.py`): only the admin adds or removes documents, rebuilds the index and saves the app settings for everyone (`page_library._app_settings_section()`, `app_settings.py`: defaults for new conversations, spending limit, guard on/off; *Reset to code defaults*). Personalisation: each user's conversations and work products are saved (`user_store.save_conversation()`) and listed on the My history page with the user's total cost.
- [x] 5. Calculate and display token usage and costs.
  - Every request (chat model, guard, embedding of each search query) is reported with its tokens (`agent.answer_question()`, `usage` events) and priced per model (`pricing.add_request()`: the cost OpenRouter reports, else tokens × the model's price). The cost line below the chat shows the chat total and tokens and what the user spent of the limit; its details popover shows tokens and requests per model and the logged-in user's total (`page_chat._costs_row()`, `user_store.total_cost()`). The Model select box shows the estimated cost of one typical answer per model (`pricing.estimate_answer_cost()`). Embedding documents shows its cost on the Knowledge base page and in the build tool. Open: the token counts of the estimate are a guess from early answers.
- [x] 6. Add visualisation of tool call results.
  - The results of the search tool are shown three ways: the "Steps" box of each answer (query, passages found), the Search steps view (each search with its passages as bars for both match values and a "cited" badge, `page_chat._passage_list()`), and the flow diagram, which lights up the tool that is running. The result of `write_document` is the work product in the Output section.
- [x] 7. Implement conversation export in various formats (PDF, CSV, JSON).
  - `export.py`, *Export* button above the chat: Markdown (questions, answers, cited references, work product; labels in the interface language), CSV (one row per message with its references; UTF-8 with BOM for Excel), JSON (the whole conversation including search steps, settings and costs, the format of the saved history). Tested in `tests/test_translations.py`. Not done: PDF (would need an extra library and a bundled font for accents; the Markdown file can be printed to PDF).
- [ ] 8. Connect to tools from a publicly available remote MCP server.
- [x] 9. Implement rate limiting and API key management.
  - Spending limit per user ($1 by default in `settings.SPENDING_LIMIT_USD`, changed by the admin in the App settings, checked before every answer in `page_chat._chat_section()` with `page_chat._spent()`): over the whole history for a logged-in user, over the browser session otherwise. The API key is never shown to users: locally from `.env`, on Streamlit Community Cloud from the app's Secrets (`config.py`, `.streamlit/secrets.toml.example`); the same for the cookie key and the GitHub token. Missing: no limit on requests per minute; a user who is not logged in can reset the limit by reloading (the credit limit of the key at OpenRouter covers that).
- [ ] 10. Add logging and monitoring.

## Hard

- [x] 1. Employ hybrid search.
  - `retrieval.search()` merges a vector search and a BM25 keyword search (LanceDB full-text index) with Reciprocal Rank Fusion; can be switched off in the sidebar to compare. Runs on the real documents with real embeddings.
- [ ] 2. Implement A/B testing for different RAG strategies.
- [ ] 3. Add automated knowledge base updates.
  - Related, not automated: `build_index.bat` syncs the index with `data/library/` (new files embedded, deleted files dropped).
- [x] 4. Add multi-language support.
  - Interface in English, Catalan and German, switched with flag buttons at the top of the sidebar (`language.py`: `picker()`, `t()`; all texts in `translations.py`; document type names and descriptions in `categories.toml`). Switching keeps the conversation, settings and login. The guard writes its reason in the interface language. Content: the documents are in Spanish and Catalan, questions can be in any language; the multilingual embedding model finds the same best passage for a question in English, Catalan or Spanish (measured 2026-11-26), and the assistant answers in the language of the question. A test checks that every text exists in every language with the same placeholders (`tests/test_translations.py`). Not translated: rare technical error messages from libraries.
- [ ] 5. Implement advanced analytics dashboard.
- [ ] 6. Implement your tools (functions) as MCP servers.
- [ ] 7. Implement an evaluation of your RAG system, using RAGAs or otherwise.

## Other work (not in `125.md`)

- Project setup with uv (Python 3.14), API key from the environment or `.env` (`config.py`, reused from the Sprint 1 project), `start_app.bat` to launch the app.
- Hosting on Streamlit Community Cloud (README): `app.py` puts `src/` on the import path; secrets from the app's Secrets; histories and app settings backed up to a separate private GitHub repository (`history_backup.py`).
- Project input: the user's own files and notes describe the project and are sent to the model with every question, without entering the knowledge base (`workspace.py`).
- Work product next to the chat, written and revised by the assistant, with download.
- Prompts in their own file (`prompts.py`); constants in `settings.py`; interface texts in `translations.py`.
- Offline tests (`tests/test_backbone.py`, `test_history_and_costs.py`, `test_build_index.py`, `test_guard.py`, `test_admin.py`, `test_flow_diagram.py`, `test_translations.py`; `uv run pytest`): 71 tests plus one check per interface text (257 in all), with fake models and a fixed price list, no API key needed.
- Command-line build tool (`build_index.py`, `build_index.bat`): updates the index from `data/library/` (`library.sync_index()`) or rebuilds it (`--rebuild`); both ask first and show the estimated embedding cost, and compact the index afterwards. The Rebuild button of the Knowledge base page asks as well.
- Login, history and costs reuse the Sprint 1 modules `auth.py`, `user_store.py` and `pricing.py`, adapted to conversations and to the LangChain agent.
- `docs/Architecture.md` summarises the components and decisions; all documentation except `README.md` and `CLAUDE.md` is in `docs/`.
