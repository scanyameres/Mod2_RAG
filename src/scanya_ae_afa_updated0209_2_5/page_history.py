"""My history page: the saved conversations of the logged-in user, with their work products.

Each conversation can be opened again on the Assistant page, and its work product downloaded.
The data comes from user_store.py; this file only draws the page.
"""

import streamlit as st

from scanya_ae_afa_updated0209_2_5 import auth, page_chat, pricing, user_store
from scanya_ae_afa_updated0209_2_5.workspace import Workspace


def _show_conversation(conversation: dict, assistant_page) -> None:
    """Draw one saved conversation: what it was about, its work product, and an Open button."""
    workspace = Workspace(**conversation["workspace"])
    usage = conversation["usage"]
    with st.container(border=True):
        details, download, open_ = st.columns([6, 2, 2], vertical_alignment="center")
        details.markdown(f"**{conversation['title']}**")
        details.caption(
            f"{conversation['updated'].replace('T', ' ')} · {len(conversation['messages'])} messages · "
            f"{', '.join(usage) or 'no model requests'} · {pricing.format_usd(pricing.total_cost(usage))}"
        )
        if workspace.document:
            details.caption(f":material/description: Work product: {workspace.document_title}")
            download.download_button(
                "Work product",
                data=workspace.export_document(),
                file_name=f"work_product_{conversation['id'][:8]}.md",
                mime="text/markdown",
                icon=":material/download:",
                key=f"download_{conversation['id']}",
                width="stretch",
            )
        if open_.button("Open", icon=":material/forum:", key=f"open_{conversation['id']}", width="stretch"):
            page_chat.open_conversation(conversation)
            st.switch_page(assistant_page)


def render(assistant_page) -> None:
    """Draw the history page. `assistant_page` is the st.Page that "Open" switches to."""
    st.title("My history")
    username = auth.current_user()
    if not username:
        st.info(
            "Log in or create an account (in the sidebar) to save your conversations and work products here.",
            icon=":material/lock:",
        )
        return
    conversations = user_store.load_conversations(username)
    if not conversations:
        st.info("No saved conversations yet. Every conversation you have on the Assistant page is saved here.")
        return
    st.caption(
        f"{len(conversations)} conversation(s) of **{username}**, last changed first · "
        f"total spent: **{pricing.format_usd(user_store.total_cost(username))}**"
    )
    for conversation in conversations:
        _show_conversation(conversation, assistant_page)
