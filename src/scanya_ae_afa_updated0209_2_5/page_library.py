"""Knowledge base page: see what is indexed; for the admin also upload, remove, rebuild and app settings.

Everyone sees the list of documents. Only the admin (auth.is_admin()) sees the rest, because
it changes the app for all users:
- upload documents (a file with the name of an existing one replaces it), remove documents,
  rebuild the index;
- App settings: the defaults of the conversation settings and the app rules (spending limit,
  guard), saved permanently (app_settings.py).

All the work is done by library.py and app_settings.py; this file only draws the page, with
the texts in the user's language (language.t(), translations.py).
Embedding documents costs API credits, so the page shows the cost of every upload and
rebuild (pricing.py).
"""

import streamlit as st

from scanya_ae_afa_updated0209_2_5 import app_settings, auth, language, library, pricing, settings
from scanya_ae_afa_updated0209_2_5.categories import Category, load_categories
from scanya_ae_afa_updated0209_2_5.embeddings import get_embeddings
from scanya_ae_afa_updated0209_2_5.language import t


def _embedding_cost(requests: list[dict]) -> str:
    """Tokens and cost of embedding requests (the `usage` list of the embedding model) as text."""
    usage = pricing.usage_of(requests)
    return t("tokens_cost", tokens=f"{pricing.total_tokens(usage):,}", cost=pricing.format_usd(pricing.total_cost(usage)))


def _upload_section(categories: list[Category]) -> None:
    """Draw the upload form and index the files when it is submitted."""
    with st.form("upload", clear_on_submit=True, border=True):
        st.subheader(t("add_documents"))
        category = st.selectbox(
            t("category"), categories, format_func=lambda category: category.label(language.current())
        )
        files = st.file_uploader(
            t("files_allowed", types=", ".join(settings.ALLOWED_EXTENSIONS), mb=settings.MAX_UPLOAD_MB),
            type=[extension.lstrip(".") for extension in settings.ALLOWED_EXTENSIONS],
            accept_multiple_files=True,
        )
        submitted = st.form_submit_button(t("add_to_library"), icon=":material/upload:", type="primary")

    if not submitted:
        return
    if not files:
        st.warning(t("choose_file"), icon=":material/warning:")
        return

    failed = 0
    embeddings = get_embeddings()  # Notes its requests, for the cost shown at the end.
    # The status box is the progress indicator: embedding a long PDF takes a while.
    category_name = category.label(language.current())
    with st.status(t("indexing", count=len(files), category=category_name), expanded=True) as status:
        for file in files:
            st.write(t("reading_file", name=file.name))
            try:
                chunks = library.add_document(file.name, file.getvalue(), category.id, embeddings)
                st.write(":material/check_circle: " + t("chunks_indexed", name=file.name, count=chunks))
            except Exception as error:  # Bad file (ValueError) or API problem: report and go on.
                failed += 1
                st.write(f":material/error: {file.name}: {error}")
        cost = t("embedding_cost", cost=_embedding_cost(embeddings.usage))
        if failed:
            status.update(label=t("finished_with_problems", count=failed, cost=cost), state="error", expanded=True)
        else:
            status.update(
                label=t("files_added", count=len(files), category=category_name, cost=cost),
                state="complete",
                expanded=False,
            )


def _documents_section(categories: list[Category], admin: bool) -> None:
    """List the indexed documents per category; for the admin each with a remove button."""
    documents = library.list_documents()
    st.subheader(t("documents_count", count=len(documents)))
    code = language.current()
    for category in categories:
        in_category = [document for document in documents if document["category"] == category.id]
        # The key gives the box its document type's shade (app.py).
        box = st.container(key=f"catlib_{category.id}")
        with box, st.expander(f"{category.label(code)} · {len(in_category)}", expanded=bool(in_category)):
            st.caption(category.tooltip(code))
            for document in in_category:
                name, details, button = st.columns([6, 4, 1], vertical_alignment="center")
                name.markdown(f":material/description: {document['source']}")
                # "sections" shows whether headings were recognised (0 = references name the page only).
                details.caption(
                    t(
                        "document_details",
                        chunks=document["chunks"],
                        sections=document["sections"],
                        date=document["added_at"].replace("T", " "),
                    )
                )
                if not admin:
                    continue
                # on_click runs before the page is redrawn, so the list is already up to date.
                button.button(
                    "",
                    icon=":material/delete:",
                    key=f"remove_{document['doc_id']}",
                    help=t("remove_document"),
                    on_click=library.remove_document,
                    args=(document["doc_id"],),
                )


def _plan_rebuild() -> None:
    """Callback of the Rebuild button: note how much would be embedded, for the question.

    A callback runs before the page is redrawn, so the Maintenance box is drawn open.
    """
    files = library.library_files()
    st.session_state["rebuild_plan"] = (len(files), library.estimate_tokens(files))


def _maintenance_section() -> None:
    """Draw the rebuild button (re-reads and re-embeds every file in data/library/).

    A rebuild costs API credits, so it takes two clicks: the first shows how much would be
    embedded (kept in st.session_state["rebuild_plan"]), the second confirms.
    """
    state = st.session_state
    with st.expander(t("maintenance"), icon=":material/build:", expanded="rebuild_plan" in state):
        st.caption(t("maintenance_caption"))
        st.button(t("rebuild_index"), icon=":material/refresh:", on_click=_plan_rebuild)

        if "rebuild_plan" in state:
            file_count, tokens = state["rebuild_plan"]
            estimate = pricing.embedding_cost(tokens)
            question = st.empty()  # Placeholder, so the question disappears once it is answered.
            with question.container():
                st.warning(
                    t("rebuild_warning", count=file_count, tokens=f"{tokens:,}", cost=pricing.format_usd(estimate)),
                    icon=":material/warning:",
                )
                confirm, cancel, _ = st.columns([2, 2, 6])
                confirmed = confirm.button(t("yes_rebuild"), type="primary", width="stretch")
                cancelled = cancel.button(t("cancel"), width="stretch")
            if confirmed or cancelled:
                del state["rebuild_plan"]
                question.empty()
            if confirmed:
                embeddings = get_embeddings()
                with st.spinner(t("rebuilding")):
                    indexed, problems = library.rebuild_index(embeddings)
                st.success(
                    t("rebuilt", count=indexed, cost=_embedding_cost(embeddings.usage)),
                    icon=":material/check_circle:",
                )
                for problem in problems:
                    st.warning(problem, icon=":material/warning:")


def _app_settings_section(categories: list[Category]) -> None:
    """Admin form: the defaults of the conversation settings and the app rules, saved for everyone."""
    current = app_settings.load()
    with st.expander(t("app_settings"), icon=":material/admin_panel_settings:"):
        st.caption(t("app_settings_caption"))
        with st.form("app_settings", border=False):
            st.markdown(t("defaults_heading"))
            active = st.multiselect(
                t("types_switched_on"),
                [category.id for category in categories],
                default=current["active_categories"],
                format_func={category.id: category.label(language.current()) for category in categories}.get,
            )
            hybrid = st.toggle(t("hybrid_search"), value=current["hybrid"])
            top_k = st.slider(t("passages_per_search"), 1, settings.TOP_K_MAX, current["top_k"])
            max_searches = st.slider(t("searches_per_answer"), 1, settings.MAX_SEARCHES_MAX, current["max_searches"])
            model_name = st.selectbox(
                t("model"), settings.CHAT_MODELS, index=settings.CHAT_MODELS.index(current["model_name"])
            )
            st.markdown(t("app_rules"))
            spending_limit = st.number_input(
                t("spending_limit"),
                min_value=0.0,
                value=current["spending_limit_usd"],
                step=0.5,
                help=t("spending_limit_help"),
            )
            guard_enabled = st.toggle(
                t("guard_setting"),
                value=current["guard_enabled"],
                help=t("guard_setting_help"),
            )
            save_column, reset_column = st.columns(2)
            saved = save_column.form_submit_button(t("save_for_everyone"), icon=":material/save:", type="primary")
            reset = reset_column.form_submit_button(
                t("reset_defaults"),
                icon=":material/restart_alt:",
                help=t("reset_defaults_help"),
            )
    if reset:
        try:
            app_settings.reset()
            # Redraw at once, so the form shows the default values.
            st.session_state["app_settings_message"] = t("reset_done")
            st.rerun()
        except Exception as error:
            st.warning(t("reset_backup_failed", error=error), icon=":material/cloud_off:")
    if message := st.session_state.pop("app_settings_message", None):
        st.success(message, icon=":material/check_circle:")
    if saved:
        try:
            app_settings.save(
                {
                    "active_categories": active,
                    "hybrid": hybrid,
                    "top_k": top_k,
                    "max_searches": max_searches,
                    "model_name": model_name,
                    "guard_enabled": guard_enabled,
                    "spending_limit_usd": spending_limit,
                }
            )
            st.success(t("settings_saved"), icon=":material/check_circle:")
        except Exception as error:  # Saved on this server, but the copy to GitHub failed.
            st.warning(t("saved_backup_failed", error=error), icon=":material/cloud_off:")


def render() -> None:
    """Draw the knowledge base page: the full page for the admin, the document list for everyone else."""
    categories = load_categories()
    admin = auth.is_admin()
    st.title(t("nav_library"))
    st.caption(t("library_caption"))
    if not admin:
        st.info(t("admin_only"), icon=":material/lock:")
        _documents_section(categories, admin=False)
        return
    # Uploads, removals and rebuilds here change only this server's disk: on the hosted app
    # they are lost at the next restart. The permanent library is data/library/ in git.
    st.info(t("changes_temporary"), icon=":material/info:")
    _upload_section(categories)
    # Reserve the place of the document list, but fill it last: a rebuild (drawn below it)
    # changes the list, and this way the list always shows the result.
    documents_area = st.container()
    _maintenance_section()
    _app_settings_section(categories)
    with documents_area:
        _documents_section(categories, admin=True)
