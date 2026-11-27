"""Language of the user interface: the flag buttons in the sidebar, and t() to look up a text.

The texts themselves are in translations.py (no Streamlit code). This module only knows which
language the user picked: the flag buttons (picker(), drawn by app.py on every page) keep it
in st.session_state["language"]. Changing it redraws the whole page in the new language; the
conversation, the settings and the login stay as they are.

The flags are drawn with CSS (FLAG_CSS) rather than as flag emojis: Windows shows flag emojis
as two letters ("GB"), and Catalonia has no flag emoji at all.

Public: current(), t(), picker(), FLAG_CSS.
"""

from urllib.parse import quote

import streamlit as st

from scanya_ae_afa_updated0209_2_5 import translations

# Each flag as a small SVG image.
_FLAGS = {
    # Union Jack, simplified.
    "en": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 60 30">'
        '<clipPath id="c"><path d="M30,15h30v15zv15h-30zh-30v-15zv-15h30z"/></clipPath>'
        '<path d="M0,0v30h60v-30z" fill="#012169"/>'
        '<path d="M0,0 60,30M60,0 0,30" stroke="#fff" stroke-width="6"/>'
        '<path d="M0,0 60,30M60,0 0,30" clip-path="url(#c)" stroke="#C8102E" stroke-width="4"/>'
        '<path d="M30,0v30M0,15h60" stroke="#fff" stroke-width="10"/>'
        '<path d="M30,0v30M0,15h60" stroke="#C8102E" stroke-width="6"/></svg>'
    ),
    # Senyera: nine stripes, yellow and red.
    "ca": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 27 18"><rect width="27" height="18" fill="#FCDD09"/>'
        + "".join(f'<rect y="{y}" width="27" height="2" fill="#DA121A"/>' for y in (2, 6, 10, 14))
        + "</svg>"
    ),
    # Black, red, gold.
    "de": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 5 3"><rect width="5" height="1" fill="#000"/>'
        '<rect y="1" width="5" height="1" fill="#D00"/><rect y="2" width="5" height="1" fill="#FFCE00"/></svg>'
    ),
}

# CSS that puts each flag in front of the code on its button (included by app.py). The
# buttons are those of the segmented control with the key "language", in the order of
# translations.LANGUAGES.
FLAG_CSS = "\n".join(
    f".st-key-language button:nth-of-type({position}) p::before {{ content: ''; display: inline-block; "
    f"width: 1.4em; height: 0.9em; margin-right: 0.4em; vertical-align: -0.1em; border-radius: 2px; "
    f"box-shadow: 0 0 0 1px rgba(128, 128, 128, 0.4); background: url(\"data:image/svg+xml,{quote(_FLAGS[code])}\") "
    f"center / cover; }}"
    for position, code in enumerate(translations.LANGUAGES, start=1)
)


def current() -> str:
    """The code of the language the user picked ("en", "ca" or "de")."""
    return st.session_state.get("language") or translations.DEFAULT_LANGUAGE


def t(key: str, **values) -> str:
    """The interface text `key` in the user's language (see translations.text())."""
    return translations.text(key, current(), **values)


def picker(disabled: bool = False) -> None:
    """Draw the flag buttons. The choice is kept in st.session_state["language"].

    `disabled`: True while the assistant answers (a click would stop the answer).
    """
    st.segmented_control(
        # The same label in every language: a widget whose label changes may lose its value.
        " / ".join(translations.text("language", code) for code in translations.LANGUAGES),
        translations.LANGUAGES,
        default=translations.DEFAULT_LANGUAGE,
        required=True,
        format_func=str.upper,  # "EN", "CA", "DE", after the flag drawn by FLAG_CSS.
        key="language",
        label_visibility="collapsed",
        width="stretch",
        disabled=disabled,
    )
