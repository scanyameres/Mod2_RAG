"""The chat agent: a LangChain agent that answers a question by calling tools (no Streamlit code).

Flow of one answer (answer_question()):
0. The guard (guard.py) lets a small model check the question for prompt injection and
   scope. A blocked question ends here, with a "blocked" event and no request to the chat model.
1. The chat model reads the system prompt (rules, active document types, the user's project
   input, the current work product, the passages found so far), the conversation and the new
   question.
2. It calls tools as needed:
   - search_documentation(query): searches the active document types and returns numbered
     passages. The model writes the query itself, so "and for hotels?" becomes a full query.
   - read_passages(numbers): returns the text of passages found earlier in the conversation
     (the system prompt lists only their locations), so a follow-up question needs no new search.
   - write_document(title, content): creates or replaces the work product next to the chat.
3. It writes the answer, citing the passage numbers.

Every request to the chat model (an answer needs one per tool round plus the final one) is
also reported with its token counts, so the page can add up the costs (pricing.py).

The model decides by itself whether to search, with which words, and how often: after
reading the passages of one search it may search again (other words, an article the passages
refer to) before it answers. Two limits:
- max_searches (Settings slider): after that many searches the search tool refuses and tells
  the model to answer with what it has; the answer still comes.
- settings.MAX_AGENT_STEPS: a safety net that stops the run with an error if the model loops.
The loop ends when the model answers without calling a tool.

The agent loop (model -> tool -> model ...) is LangChain's create_agent(). The tools are built
per answer because they are bound to the conversation's Workspace and settings. To add a tool,
write another _make_..._tool() function and put its result in the `tools` list.

Public: Event, answer_question(), validate_question().
"""

from collections.abc import Iterator
from dataclasses import dataclass, field

from langchain.agents import create_agent
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import BaseTool, tool

from scanya_ae_afa_updated0209_2_5 import config, guard, prompts, retrieval, settings
from scanya_ae_afa_updated0209_2_5.categories import Category, load_categories
from scanya_ae_afa_updated0209_2_5.embeddings import get_embeddings
from scanya_ae_afa_updated0209_2_5.workspace import Workspace


@dataclass(frozen=True)
class Event:
    """One step of an answer, yielded by answer_question() so the UI can show progress.

    kind "tool_call":   the model calls tool `tool`; `text` is the search query or the
                        document title.
    kind "tool_result": the tool answered `text`; for a search, `sources` are the passages
                        it found, best first (dicts with the Hit fields plus "number").
    kind "answer":      `text` is the final answer.
    kind "blocked":     the guard did not pass the question on; `text` is its reason for the
                        user ("" if it gave no readable verdict). It is the last event: the
                        chat model is not called.
    kind "usage":       one request to the chat model was made, one to the guard model, or one
                        to the embedding model (the query of a search); `usage` has its "model", "input_tokens",
                        "output_tokens" and "reported_cost" (USD, from OpenRouter; None if not
                        reported). The keys match pricing.add_request().
    """

    kind: str
    text: str
    tool: str = ""
    sources: list[dict] = field(default_factory=list)
    usage: dict = field(default_factory=dict)


def validate_question(question: str) -> str | None:
    """Return what is wrong with the question, else None.

    The problem is a key of translations.TEXTS, so the page can show it in the user's language:
    "question_empty", or "question_too_long" (with the values `length` and `max`).
    """
    if not question.strip():
        return "question_empty"
    if len(question) > settings.MAX_QUESTION_LENGTH:
        return "question_too_long"
    return None


def _location(source: dict, category_names: dict[str, str]) -> str:
    """One line saying where a passage is: '[3] file.pdf, section "4 Bäder › 4.2 Lüftung", page 12 (Fire safety)'."""
    section = f', section "{source["section"]}"' if source["section"] else ""
    page = f", page {source['page']}" if source["page"] else ""
    category = category_names.get(source["category"], source["category"])
    return f"[{source['number']}] {source['source']}{section}{page} ({category})"


def _make_search_tool(
    workspace: Workspace,
    active: list[Category],
    category_names: dict[str, str],
    hybrid: bool,
    top_k: int,
    max_searches: int,
    embeddings: Embeddings | None,
) -> BaseTool:
    """Build the search tool for one answer.

    It is bound to things the model must not choose itself: the active document types, the
    search mode, the number of passages per search, the number of searches allowed for this
    answer, and the workspace that numbers the passages.
    """
    searches_made = [0]  # A list, so the inner function can change it.

    @tool(response_format="content_and_artifact")
    def search_documentation(query: str) -> tuple[str, list[dict]]:
        """Search the knowledge base of building regulations and architecture documents.

        Finds passages by meaning and by exact words, so both descriptive queries
        ("minimum ceiling height in offices") and precise references ("Art. 6 Abs. 5",
        "DIN 4102-4") work. Returns numbered passages with their document, section and page.

        Args:
            query: What to look for, as a self-contained search query.
        """
        # The limit is checked here and not with the agent's step limit: that one stops the
        # run with an error, this one lets the model still write its answer.
        if searches_made[0] >= max_searches:
            return prompts.SEARCH_LIMIT_REACHED.format(limit=max_searches), []
        searches_made[0] += 1
        hits = retrieval.search(query, [category.id for category in active], hybrid, top_k, embeddings)
        if not hits:
            return prompts.NO_RESULTS, []
        sources = [workspace.add_source(hit) for hit in hits]
        passages = [f"{_location(source, category_names)}\n{source['text']}" for source in sources]
        # The text goes to the model; the list of sources goes to the UI (ToolMessage.artifact).
        return "\n\n".join(passages), sources

    return search_documentation


def _make_read_tool(workspace: Workspace, category_names: dict[str, str]) -> BaseTool:
    """Build the tool that gives the model the text of passages found earlier in the conversation.

    The system prompt lists only the location of those passages (number, document, section,
    page), to keep it short. For a follow-up question the model fetches the texts it needs by
    number: no new search, no embedding request, and exactly the passages it cited before.
    """

    @tool(response_format="content_and_artifact")
    def read_passages(numbers: list[int]) -> tuple[str, list[dict]]:
        """Read again the full text of passages found earlier in this conversation.

        Use it for follow-up questions about earlier answers, instead of searching again.

        Args:
            numbers: Passage numbers from the list of passages found so far, e.g. [1, 4].
        """
        sources = workspace.sources_by_number(numbers)
        texts = [f"{_location(source, category_names)}\n{source['text']}" for source in sources]
        unknown = sorted(set(numbers) - {source["number"] for source in sources})
        if unknown:
            texts.append(prompts.UNKNOWN_PASSAGES.format(numbers=", ".join(map(str, unknown))))
        return "\n\n".join(texts), sources

    return read_passages


def _make_document_tool(workspace: Workspace) -> BaseTool:
    """Build the tool that writes the work product into the conversation's workspace."""

    @tool
    def write_document(title: str, content: str) -> str:
        """Create or replace the work product that the user sees next to the chat.

        Use it when the user asks for a document (list of applicable rules, checklist,
        report, summary ...) or for a change to the existing one. Always pass the complete
        document, not only the changed part.

        Args:
            title: Short title of the document.
            content: The whole document in Markdown, without the title, with [n] citations.
        """
        if len(content) > settings.MAX_DOCUMENT_CHARS:
            return prompts.DOCUMENT_TOO_LONG.format(limit=settings.MAX_DOCUMENT_CHARS)
        workspace.document_title = title.strip()[:120] or "Untitled"
        workspace.document = content.strip()
        return prompts.DOCUMENT_SAVED

    return write_document


def _system_prompt(
    workspace: Workspace,
    categories: list[Category],
    active_category_ids: list[str],
    max_searches: int = settings.MAX_SEARCHES,
) -> str:
    """Fill the system prompt with the state of this conversation."""

    def bullets(selected: list[Category]) -> str:
        return "\n".join(f"- {category.name}: {category.description}" for category in selected) or "- (none)"

    category_names = {category.id: category.name for category in categories}
    document = f"Title: {workspace.document_title}\n\n{workspace.document}" if workspace.document else prompts.NO_DOCUMENT
    sources = "\n".join(_location(source, category_names) for source in workspace.sources_by_number())
    return prompts.SYSTEM_PROMPT.format(
        active_categories=bullets([category for category in categories if category.id in active_category_ids]),
        inactive_categories=bullets([category for category in categories if category.id not in active_category_ids]),
        max_searches=max_searches,
        project_input=workspace.project_input() or prompts.NO_PROJECT_INPUT,
        document=document,
        sources=sources or prompts.NO_SOURCES,
    )


def answer_question(
    question: str,
    history: list[dict],
    workspace: Workspace,
    active_category_ids: list[str],
    model_name: str = settings.CHAT_MODELS[0],
    hybrid: bool = True,
    top_k: int = settings.TOP_K,
    max_searches: int = settings.MAX_SEARCHES,
    use_guard: bool = True,
    language: str = "English",
    chat_model: BaseChatModel | None = None,
    embeddings: Embeddings | None = None,
    guard_model: BaseChatModel | None = None,
) -> Iterator[Event]:
    """Answer `question` and yield the steps as Events (tool calls, tool results, usage, the answer).

    Side effects on `workspace`: found passages are added to its sources, and write_document
    replaces its work product.

    Args:
        question: The user's new message (check it with validate_question() first).
        history: Earlier messages of the conversation, as {"role": "user" | "assistant",
            "content": str} dicts, oldest first.
        workspace: Project input, work product and sources of this conversation.
        active_category_ids: Document types switched on for this conversation.
        model_name: OpenRouter model id (one of settings.CHAT_MODELS).
        hybrid: True = vector + keyword search; False = vector search only.
        top_k: Passages the model gets per search.
        max_searches: Searches the model may make for this answer.
        use_guard: False skips the guard (the admin can switch it off, app_settings.py).
        language: Language of the interface, in English ("Catalan"), for the guard's reason.
            The answer itself is in the language of the question (prompts.SYSTEM_PROMPT).
        chat_model, embeddings, guard_model: Only for tests, to run without an API key.

    Raises:
        Whatever the model or embedding API raises (missing key, network, rate limit ...);
        the UI catches it and shows an error.
    """
    if use_guard:
        verdict = guard.check_question(question, history, guard_model, language)
        if verdict.usage:
            yield Event("usage", "", usage=verdict.usage)
        if not verdict.allowed:
            yield Event("blocked", verdict.reason)
            return

    categories = load_categories()
    category_names = {category.id: category.name for category in categories}
    active = [category for category in categories if category.id in active_category_ids]
    embeddings = embeddings or get_embeddings()  # One object per answer: it notes its requests.

    agent = create_agent(
        model=chat_model or config.get_chat_model(model_name, settings.TEMPERATURE),
        tools=[
            _make_search_tool(workspace, active, category_names, hybrid, top_k, max_searches, embeddings),
            _make_read_tool(workspace, category_names),
            _make_document_tool(workspace),
        ],
        system_prompt=_system_prompt(workspace, categories, active_category_ids, max_searches),
    )
    messages = history[-settings.MAX_HISTORY_MESSAGES :] + [{"role": "user", "content": question}]

    # stream_mode="updates" yields after every step of the agent loop: {step name: new state}.
    stream = agent.stream({"messages": messages}, {"recursion_limit": settings.MAX_AGENT_STEPS}, stream_mode="updates")
    for update in stream:
        for new_state in update.values():
            for message in (new_state or {}).get("messages", []):
                # usage_metadata: the token counts LangChain attaches to every model reply.
                if isinstance(message, AIMessage) and message.usage_metadata:
                    usage = {
                        "model": model_name,
                        "input_tokens": message.usage_metadata["input_tokens"],
                        "output_tokens": message.usage_metadata["output_tokens"],
                        "reported_cost": message.response_metadata.get("cost"),
                    }
                    yield Event("usage", "", usage=usage)
                if isinstance(message, AIMessage) and message.tool_calls:
                    for call in message.tool_calls:
                        args = call["args"]
                        if call["name"] == "read_passages":
                            summary = ", ".join(f"[{number}]" for number in args.get("numbers", []))
                        else:
                            summary = args.get("query") or args.get("title") or str(args)
                        yield Event("tool_call", str(summary), tool=call["name"])
                elif isinstance(message, AIMessage):
                    yield Event("answer", message.text)
                elif isinstance(message, ToolMessage):
                    yield Event("tool_result", message.text, tool=message.name or "", sources=message.artifact or [])
            # The searches of this step embedded their queries: report those requests as well.
            # (The fake embedding model of the tests has no `usage` list.)
            embedding_requests = getattr(embeddings, "usage", [])
            for request in embedding_requests:
                yield Event("usage", "", usage=request)
            embedding_requests.clear()
