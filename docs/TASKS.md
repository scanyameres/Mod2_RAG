# Tasks Tracker

Core and optional tasks from `125.md`. Bonus points need **at least 2 Medium and 1 Hard** optional tasks.

Legend: `[x]` done · `[~]` partially done · `[ ]` not started

## Core

### 1. RAG implementation

- [~] 1.1 Create a knowledge base relevant to the domain.
  - Done: documents are uploaded into categories on the Knowledge base page (`page_library.py` → `library.add_document()`), stored in `data/library/<category id>/` and indexed in LanceDB (`store.py`). Missing: the real documents.
- [~] 1.2 Implement standard document retrieval with embeddings.
  - Done: chunks and queries are embedded with `openai/text-embedding-3-small` (`embeddings.py`, through `config.get_client()`); `store.vector_search()` returns the nearest chunks by cosine distance. Tested offline with a fake embedding model. Missing: first run with the real API key.
- [x] 1.3 Use chunking strategies and similarity search.
  - `chunking.split_pages()`: the text is cut at recognised headings first, then by `RecursiveCharacterTextSplitter` (1,000 characters with 150 overlap, `settings.py`), never across pages. Every chunk has an exact page number and section. Similarity search: see 1.2.
- [~] 1.4 Advanced RAG: query translation and structured retrieval (from the task description).
  - Structured retrieval, done: every chunk stores its category, and both searches filter on the categories switched on in the Settings section (`store._category_filter()`). Every chunk also stores its section, the headings above it such as "Zweiter Teil … › Art. 6 Abstandsflächen" or "4 Bäder › 4.2 Lüftung" (`chunking._SectionTracker`); it is searched together with the passage and shown in every reference. Missing: a check of the heading rules on the real documents; fetching a whole article or section by its number.
  - Query translation, partly: the agent writes its own search query from the conversation, and is told to retry with the regulation's terms or language (`prompts.SYSTEM_PROMPT`). Missing: a dedicated rewrite step (keywords, translation).

### 2. Tool calling

- [~] 2.1 Implement at least 3 different tool calls.
  - Done, 3 of 3 (`agent.py`): `search_documentation(query)` searches the active document types (at most `max_searches` times per answer, slider in Settings); `read_passages(numbers)` gives back the text of passages found earlier in the conversation, so follow-up questions need no new search; `write_document(title, content)` creates or replaces the work product shown in the Output section. Missing: nothing planned.
- [~] 2.2 Functions are relevant to the domain (e.g. data analysis, calculations, API integrations).
  - The two tools are (regulation search, writing a rules document for the project). See 2.1 for the third.

### 3. Domain specialisation

- [x] 3.1 Choose a specific domain or use case.
  - Architecture and building regulations: find the rules that apply to a building project.
- [~] 3.2 Create a focused knowledge base.
  - Done: six document types in `categories.toml` (placeholders), switchable per conversation; 13 invented sample documents for them in `sample_data/`. Missing: the real documents and the final list of types.
- [x] 3.3 Implement domain-specific prompts and responses.
  - `prompts.SYSTEM_PROMPT`: answer only from the documents, quote values and article references exactly, cite passages as `[n]`, name document and page when asked for the origin, use the project input, write documents with the tool, "not legal advice" note.
- [~] 3.4 Add relevant security measures for the domain.
  - Done: LLM guard against prompt injection, off-topic and harmful requests before every answer (`guard.check_question()`, see Medium 3); question length limit (`agent.validate_question()`); upload limits on type, size and file name (`library.py`, `workspace.py`); category and document ids validated before use in database filters (`categories.py`, `store.py`); search results, project input and work product are declared material, never instructions (`prompts.py`). Missing: nothing planned.

### 4. Technical implementation

- [~] 4.1 Use LangChain with OpenRouter (OpenAI-compatible SDK) for LLM integration.
  - Done: `create_agent()` with `@tool` functions (`agent.py`), chat model from `init_chat_model(..., model_provider="openrouter")` (`config.get_chat_model()`), embeddings through the OpenAI SDK pointed at OpenRouter (`config.get_client()`, taken from the Sprint 1 project). Tested offline with a fake chat model. Missing: first run with the real API key.
- [x] 4.2 Implement proper error handling.
  - API and model errors are caught in `page_chat._answer()` and shown with `st.error` (a missing API key gets its own message); the question can be asked again. Bad files are reported per file (`ValueError` from `chunking.read_pages()`); one bad file does not stop an upload or a rebuild.
- [x] 4.3 Include user input validation.
  - Question: not empty, at most 2,000 characters. Files: PDF / TXT / MD, at most 25 MB, must contain text. Project input: capped at 30,000 characters with a warning. Category: must exist in `categories.toml`.

### 5. User interface

- [x] 5.1 Create an intuitive interface using Streamlit or Next.js.
  - Streamlit. Assistant page (`page_chat.py`) with four sections: Project input and Settings in the sidebar, Chat and Output side by side filling the window. Knowledge base as a second page (`page_library.py`).
- [x] 5.2 Show relevant context and sources.
  - Below each answer: the cited passages with document, section, page, document type, how they were found, and the exact text. Output section: References tab with every passage of the conversation; Search steps tab with all passages the model was given for each search, best first, with their match values (`page_chat._passage_list()`).
- [x] 5.3 Display tool call results.
  - "Steps" box of each answer: every search with its query and the passages found, and every write of the work product. The Search steps tab of the Output section shows the same per answer in full (`page_chat._show_search_steps()`). The work product itself is shown in the Output section.
- [x] 5.4 Include progress indicators for long operations.
  - `st.status` boxes: live steps while an answer is generated, per-file progress while documents are indexed; spinner for the index rebuild.

## Easy

- [~] 1. Add conversation history and export functionality.
  - Done: the conversation is kept for the session and sent to the model (last 12 messages); for a logged-in user every conversation is saved and can be reopened and continued from the My history page (`user_store.py`, `page_history.py`, `page_chat.open_conversation()`); the work product can be downloaded as Markdown with its reference list (`Workspace.export_document()`). Missing: export of the conversation itself.
- [x] 2. Add visualisation of RAG process.
  - Search steps tab (`page_chat._search_steps_tab()`): for each answer the path of the agent (Question → Search 1 → Search 2 → Answer), the settings used, and for every search the passages given to the model with two bars each: similarity by meaning and keyword score (`retrieval.Hit.similarity`, `keyword_score`), and a mark on the passages the answer cites. The number of passages per search and the number of searches per answer are sliders in Settings; re-read passages appear in the path as "Re-read". Tested offline with stand-in models; not yet seen with real embeddings.
- [x] 3. Include source citations in responses.
  - `[n]` citations in answers and in the work product; numbers stay fixed for the whole conversation (`Workspace.add_source()`).
- [ ] 4. Add an interactive help feature or chatbot guide.

## Medium

- [~] 1. Implement multi-model support (OpenAI, Anthropic, etc.).
  - Done: "Model" select box in Settings, options from `settings.CHAT_MODELS` (two OpenAI models, one Anthropic), passed to `config.get_chat_model()`. Missing: first run with the real API key.
- [~] 2. Add real-time data updates to knowledge base.
  - Done: uploading or removing a document on the Knowledge base page changes the index at once, so the next question already searches it. Missing: first run with the real API key.
- [x] 3. Protect your app against prompt injection.
  - `guard.check_question()`: before every answer, a small model (`settings.GUARD_MODEL`, gpt-6-luna) judges the question with structured output (`GuardVerdict`) and blocks prompt injection, off-topic and harmful requests; only allowed questions reach the chosen chat model (`agent.answer_question()`, `blocked` event; warning in `page_chat._answer()`). It sees the start of the last answer, so follow-ups pass. Fails closed. Its cost is counted. Tested offline (`tests/test_guard.py`) and with the real model on 2026-11-25: 5 legitimate questions (incl. follow-up, greeting, German) allowed, 7 attacks or off-topic requests blocked. Second layer: the system prompt treats search results, project input and work product as material, never instructions (Core 3.4). Not covered by the guard: injected text inside project files or knowledge-base documents.
- [x] 4. Add user authentication and personalisation.
  - Optional login with `streamlit-authenticator` in the sidebar (`auth.login_area()`): log in, create an account (any password for now), log out, remembered by a cookie; accounts in `config.yaml` with hashed passwords, demo accounts `sergi`, `lluis`, `turing`, `guest`. Personalisation: each user's conversations and work products are saved (`user_store.save_conversation()`, one JSON file per user in `data/users/`) and listed on the My history page, where they can be reopened; the user's total cost is shown. Tested in a headless browser with a fake chat model.
- [~] 5. Calculate and display token usage and costs.
  - Done: every chat-model request is reported by the agent with its tokens (`agent.answer_question()`, `usage` events) and priced per model (`pricing.add_request()`: the cost OpenRouter reports, else tokens × the model's price). The Costs section of the sidebar shows the chat total, tokens and requests per model, and the logged-in user's total (`page_chat._costs_section()`, `user_store.total_cost()`). Under the Model select box: the estimated cost of one typical answer with each model (`pricing.estimate_answer_cost()`, token counts in `settings.py`). First run with the real key (2026-11-24): all 22 requests were priced. Embedding requests are counted too: the query of every search in the chat costs, and documents on the Knowledge base page (`OpenRouterEmbeddings.usage`, price in `settings.py`). Missing: the token counts of the estimate are a guess until measured with documents in the knowledge base; whether OpenRouter reports the cost of embedding requests is untested.
- [ ] 6. Add visualisation of tool call results.
- [ ] 7. Implement conversation export in various formats (PDF, CSV, JSON).
- [ ] 8. Connect to tools from a publicly available remote MCP server.
- [~] 9. Implement rate limiting and API key management.
  - Done: spending limit of $1 per user (`settings.SPENDING_LIMIT_USD`, checked before every answer in `page_chat._chat_section()` with `page_chat._spent()`, shown as a bar in the Costs section): over the whole history for a logged-in user, over the browser session otherwise. The API key is never shown to users: locally from `.env`, on Streamlit Community Cloud from the app's Secrets (`config.py`, `.streamlit/secrets.toml.example`). Missing: no limit on requests per minute; a user who is not logged in can reset the limit by reloading (the credit limit of the key at OpenRouter covers that); embedding costs of the Knowledge base page are not counted per user.
- [ ] 10. Add logging and monitoring.

## Hard

- [~] 1. Employ hybrid search.
  - Done: `retrieval.search()` merges a vector search and a BM25 keyword search (LanceDB full-text index) with Reciprocal Rank Fusion; can be switched off in Settings to compare. The keyword side is tested on real text, the vector side with a fake embedding model. Missing: first run with the real API key and real documents.
- [ ] 2. Implement A/B testing for different RAG strategies.
- [ ] 3. Add automated knowledge base updates.
- [ ] 4. Add multi-language support.
- [ ] 5. Implement advanced analytics dashboard.
- [ ] 6. Implement your tools (functions) as MCP servers.
- [ ] 7. Implement an evaluation of your RAG system, using RAGAs or otherwise.

## Other work (not in `125.md`)

- Project setup with uv (Python 3.14), API key from the environment or `.env` (`config.py`, reused from the Sprint 1 project), `start_app.bat` to launch the app.
- Project input: the user's own files and notes describe the project and are sent to the model with every question, without entering the knowledge base (`workspace.py`).
- Work product next to the chat, written and revised by the assistant, with download.
- Prompts in their own file (`prompts.py`); constants in `settings.py`.
- Offline tests (`tests/test_backbone.py`, `tests/test_history_and_costs.py`, `tests/test_build_index.py`, `tests/test_guard.py`, `uv run pytest`): 46 tests with fake models and a fixed price list, no API key needed.
- Command-line build tool (`build_index.py`, `build_index.bat`): updates the index from `data/library/` (`library.sync_index()`: new files embedded, deleted files dropped) or rebuilds it (`--rebuild`); both ask first and show the estimated embedding cost. The Rebuild button of the Knowledge base page asks as well.
- Login, history and costs reuse the Sprint 1 modules `auth.py`, `user_store.py` and `pricing.py`, adapted to conversations and to the LangChain agent.
- `docs/Architecture.md` summarises the components and decisions; all documentation except `README.md` and `CLAUDE.md` is in `docs/`.
- Open: decide the real document types and documents (the committed library holds the invented `sample_data/` documents).
