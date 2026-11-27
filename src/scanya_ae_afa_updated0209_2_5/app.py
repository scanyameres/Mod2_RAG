"""Streamlit entry point: page setup, the login box, and navigation between the three pages.

Run with start_app.bat, or: uv run streamlit run src/scanya_ae_afa_updated0209_2_5/app.py

- Assistant (page_chat.py): the main page, with project input, settings, chat and output.
- Knowledge base (page_library.py): add or remove the documents the assistant searches.
- My history (page_history.py): the saved conversations of the logged-in user.

The language flags (language.py) and the login box (auth.py) are drawn here, at the top of
the sidebar, so they are on every page. Logging in is optional; the pages ask
auth.current_user() who is logged in. All interface texts are looked up with language.t()
(texts in translations.py).

The pages only draw the interface; the work is done by agent.py (chat), library.py
(documents) and user_store.py (history), which contain no Streamlit code.
"""

import sys
from pathlib import Path

import streamlit as st

# Make the package importable even when it is not installed: Streamlit only puts the folder of
# this file on the import path, not src/. Locally `uv run` installs the package anyway; on
# Streamlit Community Cloud it is not certain that the project itself gets installed.
SRC_DIR = str(Path(__file__).resolve().parents[1])
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from scanya_ae_afa_updated0209_2_5 import auth, flow_diagram, page_chat, page_history, page_library  # noqa: E402
from scanya_ae_afa_updated0209_2_5.categories import load_categories  # noqa: E402
from scanya_ae_afa_updated0209_2_5.language import FLAG_CSS, picker, t  # noqa: E402

st.set_page_config(page_title=t("page_title"), page_icon=":material/architecture:", layout="wide")

# The custom CSS of the app (the flow diagram has its own, in flow_diagram.py):
# 1. Less empty space above and beside the content (Streamlit's 5rem side padding made the
#    columns too narrow in smaller windows).
# 2. The chat and output boxes (containers with these keys in page_chat.py) fill the window
#    height, so chat and work product stay side by side without scrolling the page. Both have
#    the same height, so their tops and bottoms line up; below them there is room for the
#    question field, the chat settings and the cost line (left) and the flow diagram (right).
#    Streamlit gives a fixed-height container both "height" and "flex", so both are replaced.
# 3. A denser sidebar, so it fits on one screen: a lower header (the strip with the collapse
#    button), a little less space between elements, around the dividers and above the subheadings.
# 4. The colour code (flow_diagram.COLOURS): each control and view has the colour of the step
#    of the flow diagram it changes or shows. Green = knowledge base (Documents to search,
#    References), blue = model (the settings below the chat, Search steps), orange = work
#    product; the chat is neutral grey, like You and Answer. The output view buttons take the
#    colour of their view. The tints are see-through, so dark mode still works.
# 5. The page links at the top start where the main content starts ("Assistant" above "Chat").
# 6. No row of min/max numbers below the chat's sliders: the range is in their labels (page_chat.py).
# 7. In a narrow window the output view buttons lose their icons and get smaller, so they fit on one row.
# 8. The flags on the language buttons (language.FLAG_CSS).
# 9. Small export buttons (Markdown, CSV, JSON) in one row (page_chat._export_menu()).
# 10. Chat: the user's questions on the right, avatar on the right side, in a light grey
#     bubble (the grey of "You" in the flow diagram) as wide as their text; the assistant's
#     answers stay on the left, full width. Streamlit marks a message's content with
#     aria-label "Chat message from user". The example requests of an empty chat are
#     left-aligned buttons.
# 11. Every document type in its own shade of green (flow_diagram.CATEGORY_SHADES; the green of
#     the knowledge base as a whole is KNOWLEDGE): its name in the sidebar on a tinted
#     background and its switch, when on, in that shade; its references (in the chat, the work
#     product and the References view) and its box on the Knowledge base page with a bar in
#     that shade on the left. The elements are found by the start of their keys
#     ("category_<id>_", "ref_<id>_", "catlib_<id>", see page_chat.py and page_library.py).
BOX_HEIGHT = "calc(100vh - 27.5rem)"  # Chat box and output boxes.
BOX_MIN_HEIGHT = "12rem"  # In a low window the page scrolls rather than squeezing the boxes further.
SIDE_PADDING = "2rem"
NAV_INDENT = "1rem"  # SIDE_PADDING minus the header's own padding (1rem), measured.
KNOWLEDGE, MODEL, OUTPUT, NEUTRAL = (
    flow_diagram.COLOURS[name] for name in ("knowledge", "model", "output", "neutral")
)
CATEGORY_CSS = "".join(
    f"""
    [class*='st-key-category_{category_id}_'] label[data-selected='true'] > div:not([data-testid]) {{
        background-color: rgb({rgb}) !important; }}
    [class*='st-key-category_{category_id}_'] [data-testid='stWidgetLabel'] p {{
        display: inline; background: rgba({rgb}, 0.16); border-radius: 0.35rem; padding: 0.05rem 0.35rem;
        box-decoration-break: clone; -webkit-box-decoration-break: clone; }}
    [class*='st-key-ref_{category_id}_'] details, .st-key-catlib_{category_id} details {{
        border-left: 4px solid rgb({rgb}); }}
    [class*='st-key-ref_{category_id}_'] summary, .st-key-catlib_{category_id} summary {{
        background: rgba({rgb}, 0.08); }}
    """
    for category_id, rgb in flow_diagram.category_colours([category.id for category in load_categories()]).items()
)
st.html(
    f"""
    <style>
    [data-testid='stMainBlockContainer'] {{ padding: 3.5rem {SIDE_PADDING} 1rem {SIDE_PADDING}; }}
    [data-testid='stLayoutWrapper']:has(> .st-key-chat_box),
    [data-testid='stLayoutWrapper']:has(> .st-key-document_box),
    [data-testid='stLayoutWrapper']:has(> .st-key-references_box),
    [data-testid='stLayoutWrapper']:has(> .st-key-steps_box) {{
        height: {BOX_HEIGHT} !important; flex: 0 0 {BOX_HEIGHT} !important; min-height: {BOX_MIN_HEIGHT}; }}
    [data-testid='stSidebarHeader'] {{ height: 2rem; min-height: 2rem; margin-bottom: 0; padding-top: 0.25rem; }}
    [data-testid='stSidebarUserContent'] [data-testid='stVerticalBlock'] {{ gap: 0.6rem; }}
    [data-testid='stSidebarUserContent'] hr {{ margin: 0.75rem 0; }}
    [data-testid='stSidebarUserContent'] h3 {{ padding: 0.25rem 0 0.6rem 0; }}
    .st-key-documents_to_search {{ background: rgba({KNOWLEDGE}, 0.08); border-radius: 0.5rem; padding: 0.5rem 0.75rem; }}
    .st-key-chat_box {{ background: rgba({NEUTRAL}, 0.035); }}
    .st-key-chat_settings {{ background: rgba({MODEL}, 0.08); border-radius: 0.5rem; padding: 0.3rem 0.75rem; }}
    .st-key-document_box {{ background: rgba({OUTPUT}, 0.06); }}
    .st-key-references_box {{ background: rgba({KNOWLEDGE}, 0.06); }}
    .st-key-steps_box {{ background: rgba({MODEL}, 0.06); }}
    .st-key-output_view button:nth-of-type(1) {{ --rgb: {OUTPUT}; }}
    .st-key-output_view button:nth-of-type(2) {{ --rgb: {KNOWLEDGE}; }}
    .st-key-output_view button:nth-of-type(3) {{ --rgb: {MODEL}; }}
    .st-key-output_view button {{ background: rgba(var(--rgb), 0.08) !important;
        border-color: rgba(var(--rgb), 0.4) !important; color: inherit !important; }}
    .st-key-output_view button[kind='segmented_controlActive'] {{ background: rgba(var(--rgb), 0.26) !important;
        border-color: rgb(var(--rgb)) !important; font-weight: 600; }}
    [data-testid='stTopNav'] {{ margin-left: {NAV_INDENT}; }}
    .st-key-chat_settings [data-testid='stSliderTickBar'] {{ display: none; }}
    @media (max-width: 1250px) {{
        .st-key-output_view button span:has(> [data-testid='stIconMaterial']) {{ display: none; }}
        .st-key-output_view button {{ padding: 0 0.4rem !important; }}
        .st-key-output_view button p {{ font-size: 0.8rem; }} }}
    .st-key-export_formats button {{ min-height: 1.8rem; padding: 0.1rem 0.55rem; }}
    .st-key-export_formats button p {{ font-size: 0.85rem; }}
    [data-testid='stChatMessage']:has([aria-label='Chat message from user']) {{
        flex-direction: row-reverse; width: fit-content; max-width: 85%; margin-left: auto;
        background: rgba({NEUTRAL}, 0.12); }}
    .st-key-chat_box [class*='st-key-ask_'] button {{ justify-content: flex-start; text-align: left; }}
    {CATEGORY_CSS}
    {FLAG_CSS}
    </style>
    """
)

# Page links at the top, so the sidebar is free for the login, the assistant's input and settings.
assistant_page = st.Page(
    page_chat.render, title=t("nav_assistant"), icon=":material/forum:", url_path="assistant", default=True
)
page = st.navigation(
    [
        assistant_page,
        st.Page(page_library.render, title=t("nav_library"), icon=":material/library_books:", url_path="knowledge-base"),
        # The history page gets the assistant page, to switch to it when a conversation is opened.
        st.Page(
            lambda: page_history.render(assistant_page),
            title=t("nav_history"),
            icon=":material/history:",
            url_path="history",
        ),
    ],
    position="top",
)

# The language flags and the login box, at the top of the sidebar on every page. The login box
# must come after st.navigation():
# reading the login cookie restarts the script once, and if the pages are not known by then,
# a page opened by its address (or reloaded) is replaced by the Assistant page.
with st.sidebar:
    picker(disabled=page_chat.answer_pending())  # Disabled while an answer runs (page_chat.py).
    auth.login_area()

page.run()
