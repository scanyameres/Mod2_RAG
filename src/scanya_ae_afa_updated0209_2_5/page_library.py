"""Knowledge base page: upload documents into a category, see what is indexed, remove documents.

All the work is done by library.py; this file only draws the page. Embedding documents costs
API credits, so the page shows the cost of every upload and rebuild (pricing.py).
"""

import streamlit as st

from scanya_ae_afa_updated0209_2_5 import library, pricing, settings
from scanya_ae_afa_updated0209_2_5.categories import Category, load_categories
from scanya_ae_afa_updated0209_2_5.embeddings import get_embeddings


def _embedding_cost(requests: list[dict]) -> str:
    """Tokens and cost of embedding requests (the `usage` list of the embedding model) as text."""
    usage = {}
    for request in requests:
        pricing.add_request(usage, **request)
    return f"{pricing.total_tokens(usage):,} tokens · {pricing.format_usd(pricing.total_cost(usage))}"


def _upload_section(categories: list[Category]) -> None:
    """Draw the upload form and index the files when it is submitted."""
    with st.form("upload", clear_on_submit=True, border=True):
        st.subheader("Add documents")
        category = st.selectbox("Category", categories, format_func=lambda category: category.name)
        files = st.file_uploader(
            f"Files ({', '.join(settings.ALLOWED_EXTENSIONS)}, up to {settings.MAX_UPLOAD_MB} MB each)",
            type=[extension.lstrip(".") for extension in settings.ALLOWED_EXTENSIONS],
            accept_multiple_files=True,
        )
        submitted = st.form_submit_button("Add to knowledge base", icon=":material/upload:", type="primary")

    if not submitted:
        return
    if not files:
        st.warning("Choose at least one file first.", icon=":material/warning:")
        return

    failed = 0
    embeddings = get_embeddings()  # Notes its requests, for the cost shown at the end.
    # The status box is the progress indicator: embedding a long PDF takes a while.
    with st.status(f"Indexing {len(files)} file(s) into “{category.name}”…", expanded=True) as status:
        for file in files:
            st.write(f"Reading, splitting and embedding **{file.name}**…")
            try:
                chunks = library.add_document(file.name, file.getvalue(), category.id, embeddings)
                st.write(f":material/check_circle: {file.name}: {chunks} chunks indexed.")
            except Exception as error:  # Bad file (ValueError) or API problem: report and go on.
                failed += 1
                st.write(f":material/error: {file.name}: {error}")
        cost = f"Embedding: {_embedding_cost(embeddings.usage)}"
        if failed:
            status.update(label=f"Finished with {failed} problem(s). {cost}", state="error", expanded=True)
        else:
            status.update(
                label=f"{len(files)} file(s) added to “{category.name}”. {cost}", state="complete", expanded=False
            )


def _documents_section(categories: list[Category]) -> None:
    """List the indexed documents per category, each with a remove button."""
    documents = library.list_documents()
    st.subheader(f"Documents ({len(documents)})")
    for category in categories:
        in_category = [document for document in documents if document["category"] == category.id]
        with st.expander(f"{category.name} · {len(in_category)}", expanded=bool(in_category)):
            st.caption(category.description)
            for document in in_category:
                name, details, button = st.columns([6, 4, 1], vertical_alignment="center")
                name.markdown(f":material/description: {document['source']}")
                # "sections" shows whether headings were recognised (0 = references name the page only).
                details.caption(
                    f"{document['chunks']} chunks · {document['sections']} sections · "
                    f"added {document['added_at'].replace('T', ' ')}"
                )
                # on_click runs before the page is redrawn, so the list is already up to date.
                button.button(
                    "",
                    icon=":material/delete:",
                    key=f"remove_{document['doc_id']}",
                    help="Remove this document from the knowledge base",
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
    with st.expander("Maintenance", icon=":material/build:", expanded="rebuild_plan" in state):
        st.caption(
            "Rebuild the search index from the files in data/library/. Needed after changing the "
            "chunk size, the heading rules or the embedding model. Every document is embedded "
            "again, which costs API credits. To only add files that were copied into the folders, "
            "or drop deleted ones, run build_index.bat instead."
        )
        st.button("Rebuild index", icon=":material/refresh:", on_click=_plan_rebuild)

        if "rebuild_plan" in state:
            file_count, tokens = state["rebuild_plan"]
            estimate = tokens * settings.EMBEDDING_PRICE_PER_MILLION_TOKENS / 1_000_000
            question = st.empty()  # Placeholder, so the question disappears once it is answered.
            with question.container():
                st.warning(
                    f"All {file_count} file(s) in data/library/ will be embedded again: about {tokens:,} "
                    f"tokens, about {pricing.format_usd(estimate)}. The current index is deleted first.",
                    icon=":material/warning:",
                )
                confirm, cancel, _ = st.columns([2, 2, 6])
                confirmed = confirm.button("Yes, rebuild", type="primary", width="stretch")
                cancelled = cancel.button("Cancel", width="stretch")
            if confirmed or cancelled:
                del state["rebuild_plan"]
                question.empty()
            if confirmed:
                embeddings = get_embeddings()
                with st.spinner("Rebuilding the index…"):
                    indexed, problems = library.rebuild_index(embeddings)
                st.success(
                    f"{indexed} document(s) indexed. Embedding: {_embedding_cost(embeddings.usage)}",
                    icon=":material/check_circle:",
                )
                for problem in problems:
                    st.warning(problem, icon=":material/warning:")


def render() -> None:
    """Draw the knowledge base page."""
    categories = load_categories()
    st.title("Knowledge base")
    st.caption("The documents the assistant can search. Each document belongs to one category.")
    _upload_section(categories)
    # Reserve the place of the document list, but fill it last: a rebuild (drawn below it)
    # changes the list, and this way the list always shows the result.
    documents_area = st.container()
    _maintenance_section()
    with documents_area:
        _documents_section(categories)
