"""Assistant page, the main page of the app. Five sections:

- Project input (sidebar): the user's own files and notes about the project.
- Settings (sidebar): document types to search, hybrid search on/off, passages per search,
  chat model.
- Costs (sidebar): estimated cost of this chat per model, and the logged-in user's total.
- Chat (left): the conversation; every answer lists its references.
- Output (right): the work product the assistant writes, all references of the conversation,
  and the search steps of each answer (what was searched, which passages the model was given
  and how well they matched).

For a logged-in user (auth.py) the conversation is saved after every answer (user_store.py)
and can be opened again from the My history page (open_conversation()).

Streamlit reruns render() from top to bottom on every interaction. What must survive between
runs is kept in st.session_state:
- "messages": the conversation, a list of dicts with "role" and "content"; assistant
  messages also have "steps" (what the agent did), "sources" (the passages it found) and
  "settings" (the settings the answer was made with);
- "workspace": the conversation's Workspace (project input, work product, sources);
- "active_categories", "hybrid", "top_k", "model_name": the settings;
- "usage": requests, tokens and cost of this conversation per chat model (see pricing.py);
- "conversation_id": the id under which the conversation is saved in the user's history;
- "unsaved": True while the conversation has changes that are not in the history yet;
- "owner": the user who was logged in when the page was last drawn (None = nobody);
- "conversation": a counter, increased whenever another conversation is shown;
- "upload_round": a counter that empties the project file uploader after each upload.
"""

import re
import uuid
from collections import Counter
from dataclasses import asdict

import streamlit as st

from scanya_ae_afa_updated0209_2_5 import agent, auth, chunking, library, pricing, settings, user_store
from scanya_ae_afa_updated0209_2_5.categories import Category, load_categories
from scanya_ae_afa_updated0209_2_5.workspace import Workspace, citation_numbers

# Height of the chat and output boxes in pixels. A CSS rule in app.py stretches both to the
# window height; this value is the fallback.
BOX_HEIGHT = 560

EXAMPLE_REQUESTS = (
    "Which rules apply to the project described in my files?",
    "Write a checklist of the fire-safety requirements for this project.",
    "Where does the minimum distance to the plot boundary come from?",
)

# A saved conversation is listed in the history under its first question, cut to this length.
TITLE_LENGTH = 80


# --- State ---


def _init_state(categories: list[Category]) -> None:
    """Create the session values on the first run."""
    state = st.session_state
    state.setdefault("messages", [])
    state.setdefault("workspace", Workspace())
    state.setdefault("active_categories", [category.id for category in categories])
    state.setdefault("hybrid", True)
    state.setdefault("top_k", settings.TOP_K)
    state.setdefault("model_name", settings.CHAT_MODELS[0])
    state.setdefault("usage", {})
    state.setdefault("conversation_id", uuid.uuid4().hex)
    state.setdefault("unsaved", False)
    state.setdefault("owner", None)
    state.setdefault("conversation", 1)
    state.setdefault("upload_round", 1)


def _new_conversation(categories: list[Category]) -> None:
    """Start over: no messages, empty workspace, default search settings, no costs.

    The conversation shown before stays in the history of a logged-in user.
    """
    state = st.session_state
    state["messages"] = []
    state["workspace"] = Workspace()
    state["active_categories"] = [category.id for category in categories]
    state["hybrid"] = True
    state["top_k"] = settings.TOP_K
    state["usage"] = {}
    state["conversation_id"] = uuid.uuid4().hex
    state["unsaved"] = False
    # Widgets have these counters in their keys, so they are created anew (and empty).
    state["conversation"] += 1
    state["upload_round"] += 1


def _current_settings() -> dict:
    """The settings of the Settings section as a plain dict (saved with answers and conversations)."""
    state = st.session_state
    return {
        "active_categories": list(state["active_categories"]),
        "hybrid": state["hybrid"],
        "top_k": state["top_k"],
        "model_name": state["model_name"],
    }


# --- History of a logged-in user ---


def open_conversation(conversation: dict) -> None:
    """Show a saved conversation (a dict from user_store.py) on this page, to continue it.

    Called by the My history page, which then switches to this page.
    """
    state = st.session_state
    saved_settings = conversation["settings"]
    state["messages"] = conversation["messages"]
    state["workspace"] = Workspace(**conversation["workspace"])
    state["active_categories"] = saved_settings["active_categories"]
    state["hybrid"] = saved_settings["hybrid"]
    # Conversations saved before this setting existed have no "top_k".
    state["top_k"] = min(saved_settings.get("top_k", settings.TOP_K), settings.TOP_K_MAX)
    # The list of models may have changed since the conversation was saved.
    saved_model = saved_settings["model_name"]
    state["model_name"] = saved_model if saved_model in settings.CHAT_MODELS else settings.CHAT_MODELS[0]
    state["usage"] = conversation["usage"]
    state["conversation_id"] = conversation["id"]
    state["unsaved"] = False
    state["owner"] = auth.current_user()
    # New widget keys, so the widgets take the values of this conversation.
    state["conversation"] = state.get("conversation", 0) + 1
    state["upload_round"] = state.get("upload_round", 0) + 1


def _save_conversation(username: str) -> None:
    """Write the conversation on the page to the user's history (replaces its earlier version)."""
    state = st.session_state
    first_question = " ".join(state["messages"][0]["content"].split())
    user_store.save_conversation(
        username,
        {
            "id": state["conversation_id"],
            "title": first_question[:TITLE_LENGTH],
            "messages": state["messages"],
            "workspace": asdict(state["workspace"]),
            "settings": _current_settings(),
            "usage": state["usage"],
        },
    )
    state["unsaved"] = False


# --- Sidebar: project input ---


def _attach_project_files(uploader_key: str) -> None:
    """Callback of the uploader: read the uploaded files into the workspace."""
    state = st.session_state
    state["upload_problems"] = []
    for file in state.get(uploader_key) or []:
        try:
            state["workspace"].add_project_file(file.name, file.getvalue())
        except ValueError as error:
            state["upload_problems"].append(f"{file.name}: {error}")
    state["upload_round"] += 1  # New key = empty uploader; the files are listed below it.


def _remove_project_file(file_name: str) -> None:
    """Callback of the remove buttons."""
    st.session_state["workspace"].project_files.pop(file_name, None)


def _project_input_section(workspace: Workspace) -> None:
    """Sidebar section where the user describes the project with files and notes."""
    state = st.session_state
    st.subheader("Project input", help="Drafts, requirement lists or notes about your project. "
                 "The assistant reads them with every question. They are not added to the knowledge base.")
    uploader_key = f"project_upload_{state['upload_round']}"
    st.file_uploader(
        "Project files",
        type=[extension.lstrip(".") for extension in settings.ALLOWED_EXTENSIONS],
        accept_multiple_files=True,
        key=uploader_key,
        on_change=_attach_project_files,
        args=(uploader_key,),
    )
    for problem in state.pop("upload_problems", []):
        st.warning(problem, icon=":material/warning:")
    for file_name, text in workspace.project_files.items():
        name, button = st.columns([5, 1], vertical_alignment="center")
        name.caption(f"**{file_name}**  \n{len(text):,} characters")
        button.button(
            "",
            icon=":material/close:",
            key=f"remove_{file_name}",
            help="Remove this file from the project input",
            on_click=_remove_project_file,
            args=(file_name,),
        )
    workspace.project_notes = st.text_area(
        "Notes or requirements",
        value=workspace.project_notes,
        key=f"project_notes_{state['conversation']}",
        height=100,
        placeholder="e.g. Hotel with 40 rooms, 4 storeys, restaurant on the ground floor",
    )
    if workspace.project_input_is_cut():
        st.warning(
            f"The project input is longer than {settings.MAX_PROJECT_INPUT_CHARS:,} characters. "
            "The assistant only sees the beginning.",
            icon=":material/content_cut:",
        )


# --- Sidebar: settings ---


@st.cache_data(ttl=3600, show_spinner=False)
def _model_cost_lines() -> list[str]:
    """One line per selectable model with the estimated cost of one answer.

    Kept for an hour (st.cache_data), so the price list is not requested on every redraw,
    also not when it cannot be reached.
    """
    lines = []
    for model in settings.CHAT_MODELS:
        cost = pricing.estimate_answer_cost(model)
        lines.append(f"{model}: {pricing.format_usd(cost) if cost is not None else 'no price found'}")
    return lines


def _settings_section(categories: list[Category]) -> None:
    """Sidebar section with the search settings; stores the choices in st.session_state.

    The choices are kept in the session state, not only in the widgets: Streamlit forgets a
    widget's value when another page is opened, and the settings must survive a visit to the
    Knowledge base page.
    """
    state = st.session_state
    documents_per_category = Counter(document["category"] for document in library.list_documents())

    st.subheader("Settings")
    st.caption("Document types to search")
    active_ids = []
    for category in categories:
        switched_on = st.toggle(
            f"{category.name} ({documents_per_category[category.id]})",  # Number of documents.
            value=category.id in state["active_categories"],
            key=f"category_{category.id}_{state['conversation']}",
            help=category.description,
        )
        if switched_on:
            active_ids.append(category.id)
    state["active_categories"] = active_ids

    st.caption("Search method")
    state["hybrid"] = st.toggle(
        "Hybrid search",
        value=state["hybrid"],
        key=f"hybrid_{state['conversation']}",
        help="On: search by meaning and by exact words (article numbers, standards, values). "
        "Off: search by meaning only.",
    )
    state["top_k"] = st.slider(
        "Passages per search",
        min_value=1,
        max_value=settings.TOP_K_MAX,
        value=state["top_k"],
        key=f"top_k_{state['conversation']}",
        help="How many passages the assistant is given each time it searches. More passages can "
        "catch a rule that would be missed, but cost more tokens and can distract the model. "
        "The Search steps tab shows the passages of every search.",
    )
    state["model_name"] = st.selectbox(
        "Model",
        settings.CHAT_MODELS,
        index=settings.CHAT_MODELS.index(state["model_name"]),
        help="Below: what one typical answer would cost with each model, at OpenRouter's prices. "
        f"Typical means about {settings.TYPICAL_ANSWER_INPUT_TOKENS:,} input and "
        f"{settings.TYPICAL_ANSWER_OUTPUT_TOKENS:,} output tokens over all requests of the answer. "
        "What this chat really cost is in the Costs section.",
    )
    st.caption("Estimated cost per answer  \n" + "  \n".join(_model_cost_lines()))


# --- Sidebar: costs ---


def _costs_section(username: str | None) -> None:
    """Sidebar section with the estimated cost of this chat and the user's total."""
    usage = st.session_state["usage"]
    st.subheader(
        "Costs",
        help="Estimate in US dollars. Every request to a chat model is counted with the price of "
        "the model that answered it: the cost OpenRouter reports, or else tokens × the model's "
        "price per token. The embedding of each search query is counted too, under the embedding model.",
    )
    if not usage:
        st.caption("This chat: no requests yet.")
    else:
        st.markdown(
            f"This chat: **{pricing.format_usd(pricing.total_cost(usage))}** · {pricing.total_tokens(usage):,} tokens"
        )
        for model, totals in usage.items():
            st.caption(
                f"{model}: {pricing.format_usd(totals['cost'])} · {totals['requests']} requests · "
                f"{totals['input_tokens']:,} in / {totals['output_tokens']:,} out"
            )
        unpriced = sum(totals["unpriced"] for totals in usage.values())
        if unpriced:
            st.caption(f":material/warning: {unpriced} request(s) not included: no price found.")
    if username:
        st.markdown(f"Your total: **{pricing.format_usd(user_store.total_cost(username))}**")
        st.caption("All conversations in *My history*.")
    else:
        st.caption("Log in to save your conversations and keep a total.")


# --- References (used by the chat and the output section) ---


def _show_reference(source: dict, category_names: dict[str, str]) -> None:
    """Show one passage: its location (document, section, page) in the title, the exact text inside."""
    section = f" · {source['section']}" if source["section"] else ""
    page = f" · page {source['page']}" if source["page"] else ""
    with st.expander(f"[{source['number']}] {source['source']}{section}{page}"):
        # .get(): passages of conversations saved before the match values existed have none.
        similarity, keyword_score = source.get("similarity"), source.get("keyword_score")
        found_by = []
        if source["vector_rank"]:
            value = f", similarity {similarity:.2f}" if similarity is not None else ""
            found_by.append(f"meaning (rank {source['vector_rank']}{value})")
        if source["keyword_rank"]:
            value = f", score {keyword_score:.1f}" if keyword_score is not None else ""
            found_by.append(f"keywords (rank {source['keyword_rank']}{value})")
        category = category_names.get(source["category"], source["category"])
        st.caption(f"{category} · found by {' and '.join(found_by)}")
        st.text(source["text"])


def _show_references(text: str, sources: list[dict], category_names: dict[str, str]) -> None:
    """Below an answer: the passages it cites, each with its document, page and exact text."""
    cited = [source for source in sources if source["number"] in citation_numbers(text)]
    if cited:
        st.caption("References")
        for source in sorted(cited, key=lambda source: source["number"]):
            _show_reference(source, category_names)
    elif sources:
        # E.g. after writing the work product: the citations are in the document, not in the chat.
        numbers = ", ".join(f"[{source['number']}]" for source in sorted(sources, key=lambda source: source["number"]))
        st.caption(f"Passages found for this answer: {numbers}. See the References tab.")


# --- Chat ---


def _show_step(step: dict) -> None:
    """Show one agent step (a tool call or its result) as a line inside the status box."""
    if step["kind"] == "tool_call" and step["tool"] == "write_document":
        st.markdown(f":material/edit_document: **Write work product:** {step['text']}")
    elif step["kind"] == "tool_call":
        st.markdown(f":material/search: **Search:** {step['text']}")
    elif step["tool"] == "search_documentation":
        found = ", ".join(f"[{source['number']}] {source['source']}" for source in step["sources"])
        st.markdown(f":material/article: **Found:** {found or 'nothing in the active document types'}")


def _show_assistant_message(message: dict, category_names: dict[str, str]) -> None:
    """Show a stored assistant message: collapsed steps, the answer, its references."""
    if message["steps"]:
        with st.status("Steps", state="complete", expanded=False):
            for step in message["steps"]:
                _show_step(step)
    st.markdown(message["content"])
    _show_references(message["content"], message["sources"], category_names)


def _error_text(error: Exception) -> str:
    """Turn an exception of the answer run into a message for the user."""
    if isinstance(error, KeyError) and "API_KEY" in str(error):
        return (
            f"The API key {error} was not found. Set it as an environment variable, or copy "
            ".env.example to .env and fill it in, then restart the app."
        )
    return f"Sorry, the answer could not be generated: {error}"


def _answer(question: str, category_names: dict[str, str]) -> None:
    """Run the agent for `question`, show its progress live, and store the result."""
    state = st.session_state
    state["unsaved"] = True  # Also if the run fails: its requests are counted in the costs.
    history = [{"role": message["role"], "content": message["content"]} for message in state["messages"]]
    state["messages"].append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        steps, sources, answer = [], {}, ""
        progress = st.empty()  # Placeholder, so the status box can be removed if the run fails.
        try:
            # The status box is the progress indicator: it lists each step as it happens.
            with progress.status("Working on it…", expanded=True) as status:
                events = agent.answer_question(
                    question,
                    history,
                    state["workspace"],
                    state["active_categories"],
                    state["model_name"],
                    state["hybrid"],
                    state["top_k"],
                )
                for event in events:
                    if event.kind == "usage":
                        pricing.add_request(state["usage"], **event.usage)
                        continue
                    if event.kind == "answer":
                        answer = event.text
                        continue
                    step = {"kind": event.kind, "tool": event.tool, "text": event.text, "sources": event.sources}
                    steps.append(step)
                    _show_step(step)
                    for source in event.sources:
                        sources[source["number"]] = source
                status.update(label="Steps", state="complete", expanded=False)
        except Exception as error:  # API key missing, network problem, model error ...
            progress.empty()
            state["messages"].pop()  # Forget the question, so it can be asked again.
            st.error(_error_text(error), icon=":material/error:")
            return
        answer = answer or "I could not produce an answer. Please try rephrasing the question."
        st.markdown(answer)
        _show_references(answer, list(sources.values()), category_names)

    state["messages"].append(
        {
            "role": "assistant",
            "content": answer,
            "steps": steps,
            "sources": list(sources.values()),
            "settings": _current_settings(),
        }
    )


def _chat_section(categories: list[Category], category_names: dict[str, str]) -> None:
    """The conversation in a scrolling box, with the question field below it."""
    state = st.session_state
    heading, button = st.columns([3, 2], vertical_alignment="bottom")
    heading.subheader("Chat")
    # on_click runs before the page is redrawn, so the new conversation shows at once.
    button.button(
        "New conversation",
        icon=":material/add_comment:",
        width="stretch",
        help="Clears the chat, the project input and the output. "
        "If you are logged in, the current conversation stays in My history.",
        on_click=_new_conversation,
        args=(categories,),
    )
    box = st.container(height=BOX_HEIGHT, key="chat_box")
    with box:
        if not state["messages"]:
            if not library.list_documents():
                st.info(
                    "The knowledge base is empty. Open **Knowledge base** at the top to add documents.",
                    icon=":material/info:",
                )
            elif not state["active_categories"]:
                st.warning("All document types are switched off, so nothing can be searched.", icon=":material/warning:")
            st.caption("Ask about the rules that apply to your project. For example:")
            for example in EXAMPLE_REQUESTS:
                st.caption(f"· {example}")
        for message in state["messages"]:
            with st.chat_message(message["role"]):
                if message["role"] == "assistant":
                    _show_assistant_message(message, category_names)
                else:
                    st.markdown(message["content"])

    # st.chat_input returns the text once, when the user sends it.
    question = st.chat_input("Ask about the rules for your project")
    if question:
        with box:
            problem = agent.validate_question(question)
            if problem:
                st.warning(problem, icon=":material/warning:")
            else:
                _answer(question, category_names)


# --- Output ---


def _bar(value: float | None, maximum: float, colour: str) -> str:
    """A value as a bar of ten blocks in Streamlit Markdown; "–" if there is no value."""
    if value is None:
        return "–"
    filled = round(10 * min(max(value / maximum, 0), 1)) if maximum else 0
    return f":{colour}[{'█' * filled}]:gray[{'░' * (10 - filled)}]"


def _passage_list(sources: list[dict], cited: set[int]) -> None:
    """The passages of one search, best first, each with its two match values as bars.

    Meaning: similarity between query and passage, on a fixed scale from 0 to 1.
    Keywords: BM25 score; it has no fixed scale, so the bar is relative to the best keyword
    match of this search. (Both are explained in retrieval.py.)
    """
    best_keyword_score = max((source.get("keyword_score") or 0 for source in sources), default=0)
    lines = []
    for source in sources:
        # .get(): passages of conversations saved before the match values existed have none.
        similarity, keyword_score = source.get("similarity"), source.get("keyword_score")
        section = source["section"].split(chunking.SECTION_SEPARATOR)[-1]
        # Backslashes keep characters of file names and headings from being read as Markdown.
        label = re.sub(r"([\\`*_\[\]$#~:])", r"\\\1", " · ".join(filter(None, [source["source"], section])))
        values = [f"meaning {_bar(similarity, 1, 'green')}"]
        if similarity is not None:
            values[0] += f" {similarity:.2f}"
        if best_keyword_score:  # Nothing to show if hybrid search was off.
            values.append(
                f"keywords {_bar(keyword_score, best_keyword_score, 'blue')}"
                + (f" {keyword_score:.1f}" if keyword_score is not None else "")
            )
        mark = " :green-badge[:material/check: cited]" if source["number"] in cited else ""
        lines.append(f"**\\[{source['number']}\\]** {label}{mark}  \n:small[{' · '.join(values)}]")
    st.markdown("\n\n".join(lines))


def _settings_line(used: dict, category_names: dict[str, str]) -> str:
    """One line describing the settings an answer was made with."""
    active = used["active_categories"]
    switched_off = [name for category_id, name in category_names.items() if category_id not in active]
    return (
        f"{used['model_name']} · hybrid search {'on' if used['hybrid'] else 'off'} · "
        f"{used['top_k']} passages per search · "
        + (f"switched off: {', '.join(switched_off)}" if switched_off else "all document types on")
    )


def _show_search_steps(question: str, message: dict, workspace: Workspace, category_names: dict[str, str]) -> None:
    """Draw what the assistant did for one answer: its path, then every search with its passages."""
    steps = message["steps"]
    cited = set(citation_numbers(message["content"]))
    if any(step["tool"] == "write_document" for step in steps):
        cited |= set(citation_numbers(workspace.document))

    # The path in one line, e.g. Question → Search 1 → Search 2 → Answer.
    path, searches = [":gray-badge[:material/help: Question]"], 0
    for step in steps:
        if step["kind"] == "tool_call" and step["tool"] == "search_documentation":
            searches += 1
            path.append(f":blue-badge[:material/search: Search {searches}]")
        elif step["kind"] == "tool_call":
            path.append(":orange-badge[:material/edit_document: Write]")
    path.append(":green-badge[:material/chat: Answer]")
    st.markdown(" → ".join(path))
    st.caption(f"**Question:** {question}")
    if "settings" in message:  # Answers saved before the settings were recorded have none.
        st.caption(f"**Settings:** {_settings_line(message['settings'], category_names)}")

    queries, number, found = [], 0, set()
    for step in steps:
        if step["kind"] == "tool_call" and step["tool"] == "search_documentation":
            queries.append(step["text"])  # Its result follows in a later step.
        elif step["kind"] == "tool_call":
            st.markdown(f":material/edit_document: **Write work product** · {step['text']}")
        elif step["tool"] == "search_documentation":
            number += 1
            st.markdown(f":material/search: **Search {number}** · {queries.pop(0) if queries else ''}")
            if step["sources"]:
                _passage_list(step["sources"], cited)
                found |= {source["number"] for source in step["sources"]}
            else:
                st.caption("Nothing found in the active document types.")
    if number:
        st.markdown(
            f":material/chat: **Answer** · cites {len(cited & found)} of the {len(found)} passages found. "
            "The passage texts are in the References tab."
        )
    else:
        st.markdown(":material/chat: **Answer** · written without searching the knowledge base.")


def _search_steps_tab(category_names: dict[str, str]) -> None:
    """Content of the Search steps tab: pick an answer of the conversation, see how it was made."""
    state = st.session_state
    messages = state["messages"]
    # Every assistant message follows the question it answers.
    answers = [
        (messages[index - 1]["content"], message)
        for index, message in enumerate(messages)
        if message["role"] == "assistant"
    ]
    if not answers:
        st.caption(
            "After each answer you see here what the assistant did: every search it made, the "
            "passages it was given for it, and how well each passage matched."
        )
        return
    chosen = len(answers) - 1
    if len(answers) > 1:
        chosen = st.selectbox(
            "Answer",
            range(len(answers)),
            index=chosen,
            format_func=lambda index: f"{index + 1}. {' '.join(answers[index][0].split())[:70]}",
            # A new answer gives a new key, so the newest answer is shown.
            key=f"steps_answer_{state['conversation']}_{len(answers)}",
        )
    _show_search_steps(*answers[chosen], state["workspace"], category_names)


def _output_section(workspace: Workspace, category_names: dict[str, str]) -> None:
    """The work product, the list of all references and the search steps, in tabs next to the chat."""
    st.subheader("Output")
    document_tab, references_tab, steps_tab = st.tabs(
        [
            ":material/description: Work product",
            f":material/menu_book: References ({len(workspace.sources)})",
            ":material/account_tree: Search steps",
        ]
    )
    with steps_tab.container(height=BOX_HEIGHT, key="steps_box"):
        _search_steps_tab(category_names)
    with document_tab.container(height=BOX_HEIGHT, key="document_box"):
        if not workspace.document:
            st.caption(
                "Nothing here yet. Ask in the chat for a document, for example a checklist or a list "
                "of the rules that apply to your project. It appears here, and you can ask for changes."
            )
        else:
            title, download = st.columns([5, 3], vertical_alignment="center")
            title.markdown(f"#### {workspace.document_title}")
            file_name = re.sub(r"[^\w\- ]", "", workspace.document_title).strip().replace(" ", "_") or "work_product"
            download.download_button(
                "Download",
                data=workspace.export_document(),
                file_name=f"{file_name}.md",
                mime="text/markdown",
                icon=":material/download:",
            )
            # Display only: make the document's headings smaller than the title above ("##" -> "#####").
            st.markdown(re.sub(r"^(#{1,3}) ", r"###\1 ", workspace.document, flags=re.MULTILINE))
            cited = workspace.sources_by_number(citation_numbers(workspace.document))
            if cited:
                st.caption("References")
                for source in cited:
                    _show_reference(source, category_names)
    with references_tab.container(height=BOX_HEIGHT, key="references_box"):
        if not workspace.sources:
            st.caption("Every passage the assistant finds in this conversation is listed here, with its document and page.")
        for source in workspace.sources_by_number():
            _show_reference(source, category_names)


# --- Page ---


def render() -> None:
    """Draw the assistant page."""
    categories = load_categories()
    category_names = {category.id: category.name for category in categories}
    _init_state(categories)
    state = st.session_state
    username = auth.current_user()
    # A conversation belongs to the user who had it: after a logout it is cleared from the
    # page. One started without login is kept at login, and saved to that user's history.
    if state["owner"] not in (None, username):
        _new_conversation(categories)
    state["owner"] = username
    workspace = state["workspace"]

    with st.sidebar:
        st.divider()  # Above it: the login box, drawn by app.py.
        _project_input_section(workspace)
        st.divider()
        _settings_section(categories)
        st.divider()
        # Reserved now, filled at the end: the costs are only known after the answer has run.
        costs_area = st.empty()

    chat_column, output_column = st.columns([11, 9], gap="medium")
    with chat_column:
        _chat_section(categories, category_names)
    with output_column:
        _output_section(workspace, category_names)

    if username and state["unsaved"] and state["messages"]:
        _save_conversation(username)
    with costs_area.container():
        _costs_section(username)
