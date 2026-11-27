"""Assistant page, the main page of the app. Three areas:

- Sidebar, what belongs to the project (below the language flags and the login box of
  app.py): the project input (the user's own files and notes) and the documents to search
  (document types, hybrid search on/off).
- Centre, the interaction: the chat (every answer lists its references) with the buttons
  Export (download the conversation, export.py) and New conversation, the question field,
  then the settings a user changes from chat to chat (model, passages per search, searches per
  answer) and a cost line (this chat, spent / max of the spending limit, details).
- Right, the result: the work product the assistant writes, all references of the
  conversation or the search steps of each answer (what was searched, which passages the
  model was given and how well they matched), in a box as high as the chat box; below it the
  buttons to switch between these three (a green dot = new content) and a flow diagram of
  the answer steps (flow_diagram.py; the running step pulses).

Colours (set in app.py, key in flow_diagram.COLOURS): what belongs to a step of the flow
diagram has that step's colour: green = knowledge base (Documents to search, References),
blue = model (the settings below the question field, Search steps), orange = work product.

All texts are looked up with language.t() in the language the user picked (translations.py).

Every user can change the settings for their own conversation; a new conversation starts
with the defaults the admin saved (app_settings.py).

For a logged-in user (auth.py) the conversation is saved after every answer (user_store.py)
and can be opened again from the My history page (open_conversation()).

Streamlit reruns render() from top to bottom on every interaction. What must survive between
runs is kept in st.session_state:
- "messages": the conversation, a list of dicts with "role" and "content"; assistant
  messages also have "steps" (what the agent did), "sources" (the passages it found) and
  "settings" (the settings the answer was made with);
- "workspace": the conversation's Workspace (project input, work product, sources);
- "active_categories", "hybrid", "top_k", "max_searches", "model_name": the settings;
- "usage": requests, tokens and cost of this conversation per chat model (see pricing.py);
- "conversation_id": the id under which the conversation is saved in the user's history;
- "unsaved": True while the conversation has changes that are not in the history yet;
- "owner": the user who was logged in when the page was last drawn (None = nobody);
- "conversation": a counter, increased whenever another conversation is shown;
- "upload_round": a counter that empties the project file uploader after each upload;
- "output_view", "output_seen": the view shown in the output box, and what each view held
  when it was last shown (for the green dots, see _output_section());
- "session_cost": cost of the earlier conversations of this browser session (for the spending
  limit of a user who is not logged in, see _spent());
- "language": the language of the interface (language.py);
- "pending_question": the question just sent (question field or example button), answered in
  the run that follows (_ask()); "answering": True during that run, see render();
- "chat_notice": a warning or error about the last question, shown in the chat box (_notice()).

While an answer runs, all controls are disabled. Any click would make Streamlit start the
page again from the top, which stops the running answer halfway: its model requests are paid,
but the answer is lost. The page links and a reload can still stop it; render() then removes
the unanswered question and asks the user to ask again.
"""

import re
import uuid
from collections import Counter
from dataclasses import asdict

import streamlit as st

from scanya_ae_afa_updated0209_2_5 import (
    agent,
    app_settings,
    auth,
    chunking,
    export,
    flow_diagram,
    language,
    library,
    pricing,
    settings,
    translations,
    user_store,
)
from scanya_ae_afa_updated0209_2_5.categories import Category, load_categories
from scanya_ae_afa_updated0209_2_5.language import t
from scanya_ae_afa_updated0209_2_5.workspace import Workspace, citation_numbers

# Height of the chat and output boxes in pixels. A CSS rule in app.py stretches both to the
# window height; this value is the fallback.
BOX_HEIGHT = 560
# Minimum height of the question field in pixels (about three lines; it grows with the text).
CHAT_INPUT_HEIGHT = 96

# Example requests shown in an empty chat (keys of translations.TEXTS); a click asks them.
EXAMPLE_REQUESTS = ("example_1", "example_2", "example_3")

# Avatars in the chat: the user is the architect, the assistant the expert on the rules.
AVATARS = {"user": ":material/architecture:", "assistant": ":material/balance:"}

# The views of the output box: id -> (icon, key of its name in translations.TEXTS).
OUTPUT_VIEWS = {
    "document": (":material/description:", "work_product"),
    "references": (":material/menu_book:", "references"),
    "steps": (":material/account_tree:", "search_steps"),
}

# A saved conversation is listed in the history under its first question, cut to this length.
TITLE_LENGTH = 80


# --- State ---


def _default_settings() -> dict:
    """The Settings values a new conversation starts with: the defaults saved by the admin."""
    saved = app_settings.load()
    return {key: saved[key] for key in app_settings.SEARCH_KEYS}


def _init_state(categories: list[Category]) -> None:
    """Create the session values on the first run."""
    state = st.session_state
    state.setdefault("messages", [])
    state.setdefault("workspace", Workspace())
    for key, value in _default_settings().items():
        state.setdefault(key, value)
    state.setdefault("usage", {})
    state.setdefault("conversation_id", uuid.uuid4().hex)
    state.setdefault("unsaved", False)
    state.setdefault("owner", None)
    state.setdefault("conversation", 1)
    state.setdefault("upload_round", 1)
    state.setdefault("session_cost", 0.0)


def _new_conversation(categories: list[Category]) -> None:
    """Start over: no messages, empty workspace, the default settings, no costs.

    The conversation shown before stays in the history of a logged-in user.
    """
    state = st.session_state
    state["session_cost"] += pricing.total_cost(state["usage"])
    state["messages"] = []
    state["workspace"] = Workspace()
    state.update(_default_settings())
    state["usage"] = {}
    state["conversation_id"] = uuid.uuid4().hex
    state["unsaved"] = False
    # Widgets have these counters in their keys, so they are created anew (and empty).
    state["conversation"] += 1
    state["upload_round"] += 1


def _current_settings() -> dict:
    """The settings of this conversation as a plain dict (saved with answers and conversations)."""
    state = st.session_state
    current = {key: state[key] for key in app_settings.SEARCH_KEYS}
    current["active_categories"] = list(current["active_categories"])  # A copy, not the list in the session.
    return current


def _conversation() -> dict:
    """The conversation on the page as one dict: what is saved in the history and exported."""
    state = st.session_state
    first_question = " ".join(state["messages"][0]["content"].split()) if state["messages"] else ""
    return {
        "id": state["conversation_id"],
        "title": first_question[:TITLE_LENGTH],
        "messages": state["messages"],
        "workspace": asdict(state["workspace"]),
        "settings": _current_settings(),
        "usage": state["usage"],
    }


# --- History of a logged-in user ---


def open_conversation(conversation: dict) -> None:
    """Show a saved conversation (a dict from user_store.py) on this page, to continue it.

    Called by the My history page, which then switches to this page.
    """
    state = st.session_state
    state["messages"] = conversation["messages"]
    state["workspace"] = Workspace(**conversation["workspace"])
    # Made valid first: the models, document types or settings may have changed since it was saved.
    valid = app_settings.checked(conversation["settings"])
    state.update({key: valid[key] for key in app_settings.SEARCH_KEYS})
    state["usage"] = conversation["usage"]
    state["conversation_id"] = conversation["id"]
    state["unsaved"] = False
    state["owner"] = auth.current_user()
    # New widget keys, so the widgets take the values of this conversation.
    state["conversation"] = state.get("conversation", 0) + 1
    state["upload_round"] = state.get("upload_round", 0) + 1


def _save_conversation(username: str) -> None:
    """Write the conversation on the page to the user's history (replaces its earlier version)."""
    user_store.save_conversation(username, _conversation())
    st.session_state["unsaved"] = False


def _save_with_warning(username: str) -> None:
    """_save_conversation(), with a warning if the copy to GitHub failed (user_store.BackupError)."""
    try:
        _save_conversation(username)
    except user_store.BackupError as error:
        st.session_state["unsaved"] = False  # It is on the local disk; the next answer tries GitHub again.
        st.toast(str(error), icon=":material/cloud_off:")


# --- Spending limit ---


def _spent(username: str | None) -> float:
    """What the user spent so far, for the spending limit (app_settings.py).

    Logged in: all conversations in the history (the conversation on the page is saved after
    every answer, so it is included). Not logged in: the conversations of this browser session.
    """
    if username:
        return user_store.total_cost(username)
    return st.session_state["session_cost"] + pricing.total_cost(st.session_state["usage"])


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


def _project_input_label(workspace: Workspace) -> str:
    """Title of the collapsed project input box, saying what it holds, e.g. 'Project input · 2 files, notes'."""
    parts = []
    if workspace.project_files:
        count = len(workspace.project_files)
        parts.append(t("one_file") if count == 1 else t("n_files", count=count))
    if workspace.project_notes.strip():
        parts.append(t("notes"))
    return f"{t('project_input')} · " + (", ".join(parts) if parts else t("empty"))


def _project_input_section(workspace: Workspace) -> None:
    """Sidebar box where the user describes the project with files and notes.

    Collapsed by default to save space; its title says what it holds. The key keeps it open
    while its title changes (after an upload).
    """
    state = st.session_state
    with st.expander(
        _project_input_label(workspace),
        icon=":material/folder_open:",
        key=f"project_input_{state['conversation']}",
    ):
        _project_input_widgets(workspace)


def _project_input_widgets(workspace: Workspace) -> None:
    """Content of the project input box: uploader, list of attached files, notes."""
    state = st.session_state
    uploader_key = f"project_upload_{state['upload_round']}"
    st.file_uploader(
        t("project_files"),
        type=[extension.lstrip(".") for extension in settings.ALLOWED_EXTENSIONS],
        accept_multiple_files=True,
        key=uploader_key,
        on_change=_attach_project_files,
        args=(uploader_key,),
        help=t("project_files_help"),
        disabled=_answering(),
    )
    for problem in state.pop("upload_problems", []):
        st.warning(problem, icon=":material/warning:")
    for file_name, text in workspace.project_files.items():
        name, button = st.columns([5, 1], vertical_alignment="center")
        name.caption(f"**{file_name}**  \n{t('characters', count=f'{len(text):,}')}")
        button.button(
            "",
            icon=":material/close:",
            key=f"remove_{file_name}",
            help=t("remove_project_file"),
            on_click=_remove_project_file,
            args=(file_name,),
            disabled=_answering(),
        )
    workspace.project_notes = st.text_area(
        t("notes_label"),
        value=workspace.project_notes,
        key=f"project_notes_{state['conversation']}",
        height=80,
        placeholder=t("notes_placeholder"),
        disabled=_answering(),
    )
    if workspace.project_input_is_cut():
        st.warning(
            t("project_input_cut", limit=f"{settings.MAX_PROJECT_INPUT_CHARS:,}"),
            icon=":material/content_cut:",
        )


# --- Sidebar: documents to search ---


def _documents_section(categories: list[Category]) -> None:
    """Sidebar section: which document types are searched, and how (hybrid search on/off).

    The choices are kept in the session state, not only in the widgets: Streamlit forgets a
    widget's value when another page is opened, and the settings must survive a visit to the
    Knowledge base page.
    """
    documents_per_category = Counter(document["category"] for document in library.list_documents())

    # The key gives the box the colour of the knowledge base (app.py).
    with st.container(key="documents_to_search"):
        _documents_widgets(categories, documents_per_category)


def _documents_widgets(categories: list[Category], documents_per_category: Counter) -> None:
    """Content of the Documents to search box: a switch per document type, then hybrid search."""
    state = st.session_state
    st.subheader(t("documents_to_search"))
    active_ids = []
    for category in categories:
        # The key's start ("category_<id>_") gives the switch its document type's shade (app.py).
        switched_on = st.toggle(
            f"{category.label(language.current())} ({documents_per_category[category.id]})",  # Number of documents.
            value=category.id in state["active_categories"],
            key=f"category_{category.id}_{state['conversation']}",
            help=category.tooltip(language.current()),
            disabled=_answering(),
        )
        if switched_on:
            active_ids.append(category.id)
    state["active_categories"] = active_ids

    # Set apart, so it is not read as one more document type.
    st.caption(t("search_method"))
    state["hybrid"] = st.toggle(
        t("hybrid_search"),
        value=state["hybrid"],
        key=f"hybrid_{state['conversation']}",
        help=t("hybrid_help"),
        disabled=_answering(),
    )


# --- Chat: model and search settings, costs ---


@st.cache_data(ttl=3600, show_spinner=False)
def _model_labels(language_code: str) -> dict[str, str]:
    """Model id -> label for the model list, with the estimated cost of one typical answer.

    Kept for an hour (st.cache_data), so the price list is not requested on every redraw,
    also not when it cannot be reached. One entry per language (the text "no price").
    """
    labels = {}
    for model in settings.CHAT_MODELS:
        cost = pricing.estimate_answer_cost(model)
        if cost is not None:
            price = f"~{pricing.format_usd(cost, markdown=False)}"
        else:
            price = translations.text("no_price", language_code)
        labels[model] = f"{model.split('/')[-1]} · {price}"  # Without the provider, to fit the box.
    return labels


def _chat_settings_row() -> None:
    """Model, passages per search and searches per answer, in one row below the question field.

    Here and not in the sidebar, because they are what a user changes from chat to chat.
    """
    state = st.session_state
    # The key lets app.py colour the row (blue, like the Model step) and hide the min/max
    # numbers below these sliders (the range is in the label).
    model_column, top_k_column, searches_column = st.container(key="chat_settings").columns([4, 3, 3])
    labels = _model_labels(language.current())
    state["model_name"] = model_column.selectbox(
        t("model"),
        settings.CHAT_MODELS,
        index=settings.CHAT_MODELS.index(state["model_name"]),
        format_func=lambda model: labels[model],
        help=t(
            "model_help",
            input=f"{settings.TYPICAL_ANSWER_INPUT_TOKENS:,}",
            output=f"{settings.TYPICAL_ANSWER_OUTPUT_TOKENS:,}",
        ),
        disabled=_answering(),
    )
    state["top_k"] = top_k_column.slider(
        t("passages_range", max=settings.TOP_K_MAX),  # Short, so the label fits on one line.
        min_value=1,
        max_value=settings.TOP_K_MAX,
        value=state["top_k"],
        key=f"top_k_{state['conversation']}",
        help=t("passages_help"),
        disabled=_answering(),
    )
    state["max_searches"] = searches_column.slider(
        t("searches_range", max=settings.MAX_SEARCHES_MAX),
        min_value=1,
        max_value=settings.MAX_SEARCHES_MAX,
        value=state["max_searches"],
        key=f"max_searches_{state['conversation']}",
        help=t("searches_help"),
        disabled=_answering(),
    )


def _costs_row(username: str | None, limit: float) -> None:
    """One line below the chat: cost of this chat, what the user spent of the limit, and a popover with the details.

    The limit counts all of the user's conversations (see _spent()), so "spent" can be more
    than this chat.
    """
    usage = st.session_state["usage"]
    text_column, details_column = st.columns([9, 1], vertical_alignment="center")
    text_column.caption(
        t(
            "costs_line",
            cost=pricing.format_usd(pricing.total_cost(usage)),
            tokens=f"{pricing.total_tokens(usage):,}",
            spent=pricing.format_usd(_spent(username)),
            limit=pricing.format_usd(limit),
        )
    )
    # Tertiary = an icon without a frame, so the line stays as low as its text.
    with details_column.popover("", icon=":material/receipt_long:", help=t("cost_details"), type="tertiary"):
        st.caption(t("cost_explanation"))
        for model, totals in usage.items():
            st.caption(
                t(
                    "cost_model_line",
                    model=model,
                    cost=pricing.format_usd(totals["cost"]),
                    requests=totals["requests"],
                    input=f"{totals['input_tokens']:,}",
                    output=f"{totals['output_tokens']:,}",
                )
            )
        unpriced = sum(totals["unpriced"] for totals in usage.values())
        if unpriced:
            st.caption(":material/warning: " + t("cost_unpriced", count=unpriced))
        if username:
            st.markdown(t("your_total", cost=pricing.format_usd(user_store.total_cost(username))))
            st.caption(t("your_total_note"))


# --- References (used by the chat and the output section) ---


def _show_reference(source: dict, category_names: dict[str, str], place: str) -> None:
    """Show one passage: its location (document, section, page) in the title, the exact text inside.

    `place`: where it is drawn ("m3" = below message 3, "doc", "refs"); with the category and
    the number it makes the key of the passage's box, which app.py colours by the category.
    """
    section = f" · {source['section']}" if source["section"] else ""
    page = f" · {t('page_number', page=source['page'])}" if source["page"] else ""
    box = st.container(key=f"ref_{source['category']}_{place}_{source['number']}")
    with box, st.expander(f"[{source['number']}] {source['source']}{section}{page}"):
        # .get(): passages of conversations saved before the match values existed have none.
        similarity, keyword_score = source.get("similarity"), source.get("keyword_score")
        found_by = []
        if source["vector_rank"]:
            value = t("similarity_value", value=f"{similarity:.2f}") if similarity is not None else ""
            found_by.append(t("found_by_meaning", rank=source["vector_rank"], value=value))
        if source["keyword_rank"]:
            value = t("score_value", value=f"{keyword_score:.1f}") if keyword_score is not None else ""
            found_by.append(t("found_by_keywords", rank=source["keyword_rank"], value=value))
        category = category_names.get(source["category"], source["category"])
        st.caption(t("found_by", category=category, how=t("and").join(found_by)))
        st.text(source["text"])


def _show_references(text: str, sources: list[dict], category_names: dict[str, str], place: str) -> None:
    """Below an answer: the passages it cites, each with its document, page and exact text."""
    cited = [source for source in sources if source["number"] in citation_numbers(text)]
    if cited:
        st.caption(t("references"))
        for source in sorted(cited, key=lambda source: source["number"]):
            _show_reference(source, category_names, place)
    elif sources:
        # E.g. after writing the work product: the citations are in the document, not in the chat.
        numbers = ", ".join(f"[{source['number']}]" for source in sorted(sources, key=lambda source: source["number"]))
        st.caption(t("passages_found_for_answer", numbers=numbers))


# --- Chat ---


def _show_step(step: dict) -> None:
    """Show one agent step (a tool call or its result) as a line inside the status box."""
    if step["kind"] == "tool_call" and step["tool"] == "write_document":
        st.markdown(f":material/edit_document: **{t('step_write')}:** {step['text']}")
    elif step["kind"] == "tool_call" and step["tool"] == "read_passages":
        st.markdown(f":material/menu_book: **{t('step_reread')}:** {step['text']}")
    elif step["kind"] == "tool_call":
        st.markdown(f":material/search: **{t('step_search')}:** {step['text']}")
    elif step["tool"] == "search_documentation" and step["sources"]:
        found = ", ".join(f"[{source['number']}] {source['source']}" for source in step["sources"])
        st.markdown(f":material/article: **{t('step_found')}:** {found}")
    elif step["tool"] == "search_documentation":
        # Nothing found, or the search limit was reached: the tool's own message says which.
        st.markdown(f":material/article: {step['text']}")


def _show_assistant_message(message: dict, category_names: dict[str, str], place: str) -> None:
    """Show a stored assistant message: collapsed steps, the answer, its references (`place`: see _show_reference())."""
    if message["steps"]:
        with st.status(t("steps"), state="complete", expanded=False):
            for step in message["steps"]:
                _show_step(step)
    st.markdown(message["content"])
    _show_references(message["content"], message["sources"], category_names, place)


def _error_text(error: Exception) -> str:
    """Turn an exception of the answer run into a message for the user."""
    if isinstance(error, KeyError) and "API_KEY" in str(error):
        return t("error_api_key", name=error)
    return t("error_answer", error=error)


def _answer(question: str, category_names: dict[str, str], use_guard: bool, flow_area) -> None:
    """Run the agent for `question`, show its progress live, and store the result.

    `use_guard`: let the guard (guard.py) check the question first (an app setting).
    `flow_area`: placeholder of the flow diagram, redrawn with the running step after every event.
    """
    state = st.session_state
    code = language.current()
    state["unsaved"] = True  # Also if the run fails: its requests are counted in the costs.
    history = [{"role": message["role"], "content": message["content"]} for message in state["messages"]]
    state["messages"].append({"role": "user", "content": question})
    with st.chat_message("user", avatar=AVATARS["user"]):
        st.markdown(question)

    with st.chat_message("assistant", avatar=AVATARS["assistant"]):
        steps, sources, answer, blocked = [], {}, "", None
        progress = st.empty()  # Placeholder, so the status box can be removed if the run fails.
        stage, done = ("guard" if use_guard else "model"), {"you"}
        flow_area.html(flow_diagram.diagram_html(stage, done, use_guard, code))
        try:
            # The status box is the progress indicator: it lists each step as it happens, and
            # its label says which stage runs now (like the flow diagram).
            with progress.status(flow_diagram.stage_label(stage, code), expanded=True) as status:
                events = agent.answer_question(
                    question,
                    history,
                    state["workspace"],
                    state["active_categories"],
                    state["model_name"],
                    state["hybrid"],
                    state["top_k"],
                    state["max_searches"],
                    use_guard=use_guard,
                    language=translations.LANGUAGE_NAMES[code],
                )
                for event in events:
                    new_stage = flow_diagram.next_stage(stage, event.kind, event.tool)
                    if new_stage != stage:
                        done.add(stage)
                        stage = new_stage
                        flow_area.html(flow_diagram.diagram_html(stage, done, use_guard, code))
                        if stage in flow_diagram.STAGES_WITH_LABEL:
                            status.update(label=flow_diagram.stage_label(stage, code))
                    if event.kind == "usage":
                        pricing.add_request(state["usage"], **event.usage)
                        continue
                    if event.kind == "answer":
                        answer = event.text
                        continue
                    if event.kind == "blocked":  # The guard did not pass the question on.
                        blocked = event.text
                        continue
                    step = {"kind": event.kind, "tool": event.tool, "text": event.text, "sources": event.sources}
                    steps.append(step)
                    _show_step(step)
                    for source in event.sources:
                        sources[source["number"]] = source
                status.update(label=t("steps"), state="complete", expanded=False)
        except Exception as error:  # API key missing, network problem, model error ...
            progress.empty()
            flow_area.html(flow_diagram.diagram_html(None, done, use_guard, code))
            state["messages"].pop()  # Forget the question, so it can be asked again.
            _notice("error", _error_text(error), ":material/error:")
            return
        done.add(stage)  # The last stage (the answer, or the guard that blocked) is done too.
        flow_area.html(flow_diagram.diagram_html(None, done, use_guard, code))
        if blocked is not None:
            progress.empty()
            state["messages"].pop()  # A blocked question does not become part of the conversation.
            # The guard's reason, or (no readable verdict) a general message.
            _notice("warning", t("guard_blocked", reason=blocked) if blocked else t("guard_no_verdict"), ":material/shield:")
            return
        answer = answer or t("no_answer")
        st.markdown(answer)
        # The place of the message this answer becomes (the user's question is already stored).
        _show_references(answer, list(sources.values()), category_names, f"m{len(state['messages'])}")

    state["messages"].append(
        {
            "role": "assistant",
            "content": answer,
            "steps": steps,
            "sources": list(sources.values()),
            "settings": _current_settings(),
        }
    )


def _export_menu() -> None:
    """The Export button: a popover with a download per format (export.py)."""
    state = st.session_state
    with st.popover(
        t("export"),
        icon=":material/download:",
        help=t("export_help"),
        disabled=not state["messages"] or _answering(),
        width="stretch",
    ):
        conversation = _conversation()
        name = f"conversation_{state['conversation_id'][:8]}"
        formats = (
            ("Markdown", "export_markdown", export.to_markdown(conversation, language.current()), "md", "text/markdown"),
            ("CSV", "export_csv", export.to_csv(conversation), "csv", "text/csv"),
            ("JSON", "export_json", export.to_json(conversation), "json", "application/json"),
        )
        # One row of small buttons (made smaller by the CSS for "export_formats" in app.py).
        row = st.container(key="export_formats", horizontal=True, gap="xxsmall")
        for label, help_key, data, extension, mime in formats:
            row.download_button(
                label,
                data=data,
                file_name=f"{name}.{extension}",
                mime=mime,
                help=t(help_key),
                width="content",
            )


def answer_pending() -> bool:
    """True from the moment a question is sent until the run that answers it has begun.

    app.py asks it before drawing the language flags, which are then disabled like all
    controls of this page (see render()).
    """
    return "pending_question" in st.session_state


def _answering() -> bool:
    """True in the run that answers a question: the controls are drawn disabled (see render())."""
    return st.session_state.get("answering", False)


def _ask(question: str) -> None:
    """Callback of the example buttons: `question` is answered in the run that follows the click."""
    st.session_state["pending_question"] = question


def _submit_question() -> None:
    """Callback of the question field: what the user typed is answered in the run that follows."""
    question = st.session_state.get("question_field")
    if question:
        _ask(question)


def _notice(kind: str, text: str, icon: str) -> None:
    """Keep a warning ("warning") or error ("error") for the chat box.

    Shown in the next run: render() redraws the page right after answering.
    """
    st.session_state["chat_notice"] = (kind, text, icon)


def _chat_section(categories: list[Category], category_names: dict[str, str], rules: dict, flow_area, question):
    """The conversation in a scrolling box; below it the question field, the chat settings and the cost line.

    `question`: the question to answer in this run (None = none, see render()).
    `rules`: the app settings (app_settings.load()), for the spending limit and the guard.
    `flow_area`: placeholder of the flow diagram (see _answer()).
    Returns the placeholder of the cost line, filled by render() once the answer has run.
    """
    state = st.session_state
    heading, export_column, new_column = st.columns([3, 2, 3], vertical_alignment="bottom")
    heading.subheader(t("chat"))
    # Filled at the end: the export must include the answer this run may add.
    export_area = export_column.empty()
    # on_click runs before the page is redrawn, so the new conversation shows at once.
    new_column.button(
        t("new_conversation"),
        icon=":material/add_comment:",
        width="stretch",
        help=t("new_conversation_help"),
        on_click=_new_conversation,
        args=(categories,),
        disabled=_answering(),
    )
    box = st.container(height=BOX_HEIGHT, key="chat_box")
    with box:
        if not state["messages"] and not question:
            if not library.list_documents():
                st.info(t("knowledge_base_empty"), icon=":material/info:")
            elif not state["active_categories"]:
                st.warning(t("all_switched_off"), icon=":material/warning:")
            names = ", ".join(category.label(language.current()) for category in categories)
            st.markdown(f":material/waving_hand: {t('welcome', categories=names)}")
            st.caption(t("ask_intro"))
            for request in EXAMPLE_REQUESTS:
                st.button(
                    t(request),
                    icon=":material/chat_bubble:",
                    key=f"ask_{request}",
                    on_click=_ask,
                    args=(t(request),),
                )
        for index, message in enumerate(state["messages"]):
            with st.chat_message(message["role"], avatar=AVATARS[message["role"]]):
                if message["role"] == "assistant":
                    _show_assistant_message(message, category_names, f"m{index}")
                else:
                    st.markdown(message["content"])
        notice = state.pop("chat_notice", None)  # About the question of the last run.
        if notice:
            kind, text, icon = notice
            (st.error if kind == "error" else st.warning)(text, icon=icon)

    # Inside a column the question field is drawn here, below the chat box. Taller than one
    # line, so longer questions are readable while typing. Sending calls _submit_question().
    st.chat_input(
        t("chat_placeholder"),
        key="question_field",
        height=CHAT_INPUT_HEIGHT,
        on_submit=_submit_question,
        disabled=_answering(),
    )
    # Drawn before the question is answered, so the answer uses the settings shown.
    _chat_settings_row()
    # Reserved now, filled at the end: the costs are only known after the answer has run.
    costs_area = st.empty()

    if question:
        with box:
            problem = agent.validate_question(question)
            if problem:
                _notice(
                    "warning",
                    t(problem, length=f"{len(question):,}", max=f"{settings.MAX_QUESTION_LENGTH:,}"),
                    ":material/warning:",
                )
            elif _spent(auth.current_user()) >= (limit := rules["spending_limit_usd"]):
                _notice("warning", t("spending_limit_reached", limit=pricing.format_usd(limit)), ":material/money_off:")
            else:
                _answer(question, category_names, rules["guard_enabled"], flow_area)
    with export_area.container():
        _export_menu()
    return costs_area


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
        values = [f"{t('meaning')} {_bar(similarity, 1, 'primary')}"]
        if similarity is not None:
            values[0] += f" {similarity:.2f}"
        if best_keyword_score:  # Nothing to show if hybrid search was off.
            values.append(
                f"{t('keywords')} {_bar(keyword_score, best_keyword_score, 'blue')}"
                + (f" {keyword_score:.1f}" if keyword_score is not None else "")
            )
        mark = f" :primary-badge[:material/check: {t('cited')}]" if source["number"] in cited else ""
        lines.append(f"**\\[{source['number']}\\]** {label}{mark}  \n:small[{' · '.join(values)}]")
    st.markdown("\n\n".join(lines))


def _settings_line(used: dict, category_names: dict[str, str]) -> str:
    """One line describing the settings an answer was made with."""
    active = used["active_categories"]
    switched_off = [name for category_id, name in category_names.items() if category_id not in active]
    parts = [
        used["model_name"],
        t("settings_hybrid", state=t("on") if used["hybrid"] else t("off")),
        t("settings_top_k", count=used["top_k"]),
    ]
    if "max_searches" in used:  # Answers saved before this setting existed have none.
        parts.append(t("settings_searches", count=used["max_searches"]))
    parts.append(t("settings_switched_off", names=", ".join(switched_off)) if switched_off else t("settings_all_on"))
    return " · ".join(parts)


def _show_search_steps(question: str, message: dict, workspace: Workspace, category_names: dict[str, str]) -> None:
    """Draw what the assistant did for one answer: its path, then every search with its passages."""
    steps = message["steps"]
    cited = set(citation_numbers(message["content"]))
    if any(step["tool"] == "write_document" for step in steps):
        cited |= set(citation_numbers(workspace.document))

    # The path in one line, e.g. Question → Search 1 → Search 2 → Answer, in the colours of the
    # flow diagram: knowledge base = primary (green), work product = orange, the rest grey.
    path, searches = [f":gray-badge[:material/help: {t('question')}]"], 0
    for step in steps:
        if step["kind"] == "tool_call" and step["tool"] == "search_documentation":
            searches += 1
            path.append(f":primary-badge[:material/search: {t('search_n', number=searches)}]")
        elif step["kind"] == "tool_call" and step["tool"] == "read_passages":
            path.append(f":primary-badge[:material/menu_book: {t('reread')}]")
        elif step["kind"] == "tool_call":
            path.append(f":orange-badge[:material/edit_document: {t('write')}]")
    path.append(f":gray-badge[:material/chat: {t('answer')}]")
    st.markdown(" → ".join(path))
    st.caption(f"**{t('question')}:** {question}")
    if "settings" in message:  # Answers saved before the settings were recorded have none.
        st.caption(f"**{t('settings')}:** {_settings_line(message['settings'], category_names)}")

    queries, number, found = [], 0, set()
    for step in steps:
        if step["kind"] == "tool_call" and step["tool"] == "search_documentation":
            queries.append(step["text"])  # Its result follows in a later step.
        elif step["kind"] == "tool_call" and step["tool"] == "read_passages":
            st.markdown(f":material/menu_book: **{t('step_reread')}** · {step['text']} ({t('reread_note')})")
        elif step["kind"] == "tool_call":
            st.markdown(f":material/edit_document: **{t('step_write')}** · {step['text']}")
        elif step["tool"] == "search_documentation":
            number += 1
            st.markdown(f":material/search: **{t('search_n', number=number)}** · {queries.pop(0) if queries else ''}")
            if step["sources"]:
                _passage_list(step["sources"], cited)
                found |= {source["number"] for source in step["sources"]}
            else:
                st.caption(step["text"])  # Nothing found, or the search limit was reached.
    if number:
        st.markdown(f":material/chat: **{t('answer')}** · {t('answer_cites', cited=len(cited & found), found=len(found))}")
    else:
        st.markdown(f":material/chat: **{t('answer')}** · {t('answer_without_search')}")


def _search_steps_tab(category_names: dict[str, str]) -> None:
    """Content of the Search steps view: pick an answer of the conversation, see how it was made."""
    state = st.session_state
    messages = state["messages"]
    # Every assistant message follows the question it answers.
    answers = [
        (messages[index - 1]["content"], message)
        for index, message in enumerate(messages)
        if message["role"] == "assistant"
    ]
    if not answers:
        st.caption(t("steps_empty"))
        return
    chosen = len(answers) - 1
    if len(answers) > 1:
        chosen = st.selectbox(
            t("answer"),
            range(len(answers)),
            index=chosen,
            format_func=lambda index: f"{index + 1}. {' '.join(answers[index][0].split())[:70]}",
            # A new answer gives a new key, so the newest answer is shown.
            key=f"steps_answer_{state['conversation']}_{len(answers)}",
            disabled=_answering(),
        )
    _show_search_steps(*answers[chosen], state["workspace"], category_names)


def _work_product_view(workspace: Workspace, category_names: dict[str, str]) -> None:
    """Content of the Work product view: the document the assistant wrote, with download and references."""
    if not workspace.document:
        st.caption(t("document_empty"))
        return
    title, download = st.columns([5, 3], vertical_alignment="center")
    title.markdown(f"#### {workspace.document_title}")
    file_name = re.sub(r"[^\w\- ]", "", workspace.document_title).strip().replace(" ", "_") or "work_product"
    download.download_button(
        t("download"),
        data=workspace.export_document(language.current()),
        file_name=f"{file_name}.md",
        mime="text/markdown",
        icon=":material/download:",
        disabled=_answering(),
    )
    # Display only: make the document's headings smaller than the title above ("##" -> "#####").
    st.markdown(re.sub(r"^(#{1,3}) ", r"###\1 ", workspace.document, flags=re.MULTILINE))
    cited = workspace.sources_by_number(citation_numbers(workspace.document))
    if cited:
        st.caption(t("references"))
        for source in cited:
            _show_reference(source, category_names, "doc")


def _references_view(workspace: Workspace, category_names: dict[str, str]) -> None:
    """Content of the References view: every passage found in this conversation."""
    if not workspace.sources:
        st.caption(t("references_empty"))
    for source in workspace.sources_by_number():
        _show_reference(source, category_names, "refs")


def _output_versions(workspace: Workspace) -> dict:
    """Something per output view that changes when its content changes (to see what is new)."""
    return {
        "document": workspace.document,
        "references": len(workspace.sources),
        "steps": sum(message["role"] == "assistant" for message in st.session_state["messages"]),
    }


def _output_section(workspace: Workspace, category_names: dict[str, str]) -> None:
    """The work product, all references or the search steps, in a box as high as the chat box.

    The buttons to switch between them are below the box (a segmented control: st.tabs always
    puts its buttons on top, and forgets the chosen tab when a label changes). A green dot on a
    button means its view has new content the user has not seen yet: st.session_state
    ["output_seen"] keeps, per view, what it held when it was last shown (_output_versions()).
    """
    state = st.session_state
    st.subheader(t("output"))
    versions = _output_versions(workspace)
    seen = state.get("output_seen")
    if seen is None or seen["conversation"] != state["conversation"]:
        # Another conversation is shown (new, or opened from the history): nothing is new.
        seen = state["output_seen"] = {"conversation": state["conversation"], **versions}
    view = state.get("output_view") or "document"  # The choice of the buttons drawn below.
    seen[view] = versions[view]  # What is shown now counts as seen.

    with st.container(height=BOX_HEIGHT, key=f"{view}_box"):
        if view == "document":
            _work_product_view(workspace, category_names)
        elif view == "references":
            _references_view(workspace, category_names)
        else:
            _search_steps_tab(category_names)

    def label(option: str) -> str:
        icon, name_key = OUTPUT_VIEWS[option]
        count = f" ({len(workspace.sources)})" if option == "references" else ""
        dot = " :primary[⬤]" if versions[option] != seen[option] else ""
        return f"{icon} {t(name_key)}{count}{dot}"

    st.segmented_control(
        "Output view",
        list(OUTPUT_VIEWS),
        default="document",
        required=True,
        format_func=label,
        key="output_view",
        label_visibility="collapsed",
        width="stretch",
        wrap=False,  # One row; in a narrow window app.py hides the icons so it fits.
        disabled=_answering(),
    )


# --- Page ---


def render() -> None:
    """Draw the assistant page."""
    categories = load_categories()
    category_names = {category.id: category.label(language.current()) for category in categories}
    _init_state(categories)
    state = st.session_state
    username = auth.current_user()
    # A conversation belongs to the user who had it: after a logout it is cleared from the
    # page. One started without login is kept at login, and saved to that user's history.
    if state["owner"] not in (None, username):
        _new_conversation(categories)
    state["owner"] = username
    # A question without answer: its answer was stopped halfway (the page was left or reloaded
    # while it ran). Removed, so the conversation stays a list of question-answer pairs.
    if state["messages"] and state["messages"][-1]["role"] == "user":
        state["messages"].pop()
        _notice("warning", t("answer_interrupted"), ":material/replay:")
    # A question sent since the last run (_ask()) is answered in this run, with all controls
    # disabled; afterwards the page is redrawn with them enabled again (end of this function).
    question = state.pop("pending_question", None)
    state["answering"] = question is not None
    workspace = state["workspace"]
    rules = app_settings.load()  # Spending limit and guard, set by the admin; read once per run.

    with st.sidebar:
        # Above it: the language flags and the login box, drawn by app.py.
        _project_input_section(workspace)
        st.divider()
        _documents_section(categories)

    chat_column, output_column = st.columns([11, 9], gap="medium")
    with output_column:
        # Drawn before the chat; an answer that changes it shows in the redraw after answering.
        _output_section(workspace, category_names)
        # Must exist before the chat: _answer() redraws it.
        flow_area = st.empty()
        flow_area.html(flow_diagram.diagram_html(guard_on=rules["guard_enabled"], language=language.current()))
    with chat_column:
        costs_area = _chat_section(categories, category_names, rules, flow_area, question)

    if username and state["unsaved"] and state["messages"]:
        _save_with_warning(username)
    with costs_area.container():
        _costs_row(username, rules["spending_limit_usd"])
    if question is not None:
        st.rerun()  # Answered: redraw with the controls enabled again.
