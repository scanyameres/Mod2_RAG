"""Streamlit entry point: page setup, the login box, and navigation between the three pages.

Run with start_app.bat, or: uv run streamlit run src/scanya_ae_afa_updated0209_2_5/app.py

- Assistant (page_chat.py): the main page, with project input, settings, chat and output.
- Knowledge base (page_library.py): add or remove the documents the assistant searches.
- My history (page_history.py): the saved conversations of the logged-in user.

The login box (auth.py) is drawn here, at the top of the sidebar, so it is on every page.
Logging in is optional; the pages ask auth.current_user() who is logged in.

The pages only draw the interface; the work is done by agent.py (chat), library.py
(documents) and user_store.py (history), which contain no Streamlit code.
"""

import streamlit as st

from scanya_ae_afa_updated0209_2_5 import auth, page_chat, page_history, page_library

st.set_page_config(page_title="Building Rules Assistant", page_icon=":material/architecture:", layout="wide")

# The only custom CSS of the app:
# 1. Less empty space above the content.
# 2. The chat and output boxes (containers with these keys in page_chat.py) fill the window
#    height, so chat and work product stay side by side without scrolling the page.
#    Streamlit gives a fixed-height container both "height" and "flex", so both are replaced.
CHAT_BOX_HEIGHT = "calc(100vh - 14.5rem)"
OUTPUT_BOX_HEIGHT = "calc(100vh - 14rem)"
st.html(
    f"""
    <style>
    [data-testid='stMainBlockContainer'] {{ padding-top: 3.5rem; padding-bottom: 1rem; }}
    [data-testid='stLayoutWrapper']:has(> .st-key-chat_box) {{
        height: {CHAT_BOX_HEIGHT} !important; flex: 0 0 {CHAT_BOX_HEIGHT} !important; min-height: 20rem; }}
    [data-testid='stLayoutWrapper']:has(> .st-key-document_box),
    [data-testid='stLayoutWrapper']:has(> .st-key-references_box),
    [data-testid='stLayoutWrapper']:has(> .st-key-steps_box) {{
        height: {OUTPUT_BOX_HEIGHT} !important; flex: 0 0 {OUTPUT_BOX_HEIGHT} !important; min-height: 20rem; }}
    </style>
    """
)

# Page links at the top, so the sidebar is free for the login, the assistant's input and settings.
assistant_page = st.Page(
    page_chat.render, title="Assistant", icon=":material/forum:", url_path="assistant", default=True
)
page = st.navigation(
    [
        assistant_page,
        st.Page(page_library.render, title="Knowledge base", icon=":material/library_books:", url_path="knowledge-base"),
        # The history page gets the assistant page, to switch to it when a conversation is opened.
        st.Page(
            lambda: page_history.render(assistant_page),
            title="My history",
            icon=":material/history:",
            url_path="history",
        ),
    ],
    position="top",
)

# The login box, at the top of the sidebar on every page. It must come after st.navigation():
# reading the login cookie restarts the script once, and if the pages are not known by then,
# a page opened by its address (or reloaded) is replaced by the Assistant page.
with st.sidebar:
    auth.login_area()

page.run()
