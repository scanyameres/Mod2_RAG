"""Optional user login with streamlit-authenticator, configured from config.yaml in the project root.

Taken from the Sprint 1 project (scanya-AE.AFA.updated0209.1.6, auth.py). Changed for this
project: the box is drawn in the sidebar (app.py), any non-empty password is accepted for a
new account (see _AnyPassword), and current_user() tells the pages who is logged in.

config.yaml holds the user accounts, with passwords stored as bcrypt hashes, and the key that
signs the login cookie. It is committed to git on purpose (a dummy account for now); a real
deployment would keep it out of git. If it does not exist, it is created on first start with
no users and a random cookie key; users then sign up with the "Create account" form, which
streamlit-authenticator writes back to the same file.

The app works without logging in. Logging in adds the history (user_store.py).

Public functions: login_area() (draws the login box), current_user().
"""

import secrets
import time

import streamlit as st
import streamlit_authenticator as stauth
import yaml
from streamlit_authenticator.utilities import LoginError, Validator

from scanya_ae_afa_updated0209_2_5 import settings

# Seconds to wait after a login or logout before the page is redrawn. The login cookie is
# written (or removed) by a small component in the browser; redrawing at once would remove
# that component before it has done its work, and the login would not survive a page reload.
COOKIE_WAIT_SECONDS = 1.0


class _AnyPassword(Validator):
    """The library's input checks, without its password rules.

    By default a new password needs 8-20 characters with a lowercase letter, an uppercase
    letter, a digit and a special character. For now any password is accepted (the form
    itself already refuses an empty one). To get the default rules back, delete this class
    and the two arguments `validator=` and `password_instructions=` in _get_authenticator().
    """

    def validate_password(self, password: str) -> bool:
        return True


def current_user() -> str | None:
    """Username of the logged-in user, or None. Valid after login_area() ran in this page run."""
    if st.session_state.get("authentication_status"):
        return st.session_state["username"]
    return None


def login_area() -> str | None:
    """Draw the login / create-account box, or "signed in as" + logout. Returns the username or None.

    streamlit-authenticator keeps the login state in st.session_state ("authentication_status",
    "username", "name"). After logging in or out, the page is redrawn (st.rerun) once the login
    cookie had time to be written or removed.
    """
    authenticator = _get_authenticator()
    if st.session_state.get("authentication_status"):
        name_column, logout_column = st.columns((3, 2), vertical_alignment="center")
        name_column.caption(f"Signed in as **{st.session_state['username']}**")
        with logout_column:
            authenticator.logout(location="main", key="Logout")
        if not st.session_state.get("authentication_status"):
            time.sleep(COOKIE_WAIT_SECONDS)
            st.rerun()  # just logged out: redraw with the login box
        return st.session_state["username"]

    # Not logged in. login() also restores a session from the login cookie, so it must run on
    # every page load; it is drawn inside the (collapsed) expander.
    with st.expander("Log in or create an account", icon=":material/lock:"):
        st.caption("Optional. Logged in, your conversations and work products are saved in *My history*.")
        login_tab, signup_tab = st.tabs(("Log in", "Create account"))
        with login_tab:
            try:
                authenticator.login(location="main", key="Login")
            except LoginError as error:
                st.error(str(error))
            if st.session_state.get("authentication_status") is False:
                st.error("Username or password is incorrect.")
        with signup_tab:
            try:
                _, new_username, _ = authenticator.register_user(
                    location="main", captcha=False, password_hint=False
                )
                if new_username:
                    st.success(f"Account **{new_username}** created. You can now log in.")
            except Exception as error:  # e.g. username taken, passwords don't match
                st.error(str(error))
    if st.session_state.get("authentication_status"):
        time.sleep(COOKIE_WAIT_SECONDS)
        st.rerun()  # just logged in: redraw with the "signed in" line
    return None


def _get_authenticator() -> stauth.Authenticate:
    """Return the authenticator for this page run, creating config.yaml first if needed."""
    if not settings.AUTH_CONFIG_FILE.exists():
        _create_config()
    config = yaml.safe_load(settings.AUTH_CONFIG_FILE.read_text(encoding="utf-8"))
    # Passing the file path (not a dict) lets the library save new accounts to the file itself.
    return stauth.Authenticate(
        str(settings.AUTH_CONFIG_FILE),
        cookie_name=config["cookie"]["name"],
        cookie_key=config["cookie"]["key"],
        cookie_expiry_days=config["cookie"]["expiry_days"],
        validator=_AnyPassword(),
        password_instructions="Any password is accepted for now.",  # Help text of the password field.
    )


def _create_config() -> None:
    """Write a starting config.yaml: no users yet and a random secret for the login cookie."""
    config = {
        "credentials": {"usernames": {}},
        "cookie": {
            "name": "building_rules_login",
            "key": secrets.token_hex(32),
            "expiry_days": 30,
        },
    }
    settings.AUTH_CONFIG_FILE.write_text(yaml.safe_dump(config), encoding="utf-8")
