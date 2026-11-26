"""Optional user login with streamlit-authenticator, configured from config.yaml in the project root.

Taken from the Sprint 1 project (scanya-AE.AFA.updated0209.1.6, auth.py). Changed for this
project: the box is drawn in the sidebar (app.py), any non-empty password is accepted for a
new account (see _AnyPassword), and current_user() tells the pages who is logged in.

config.yaml holds the user accounts, with passwords stored as bcrypt hashes, and the name and
lifetime of the login cookie. It is committed to git on purpose, with the demo accounts listed in the README. If it
does not exist, it is created on first start with no users; users then sign up with the
"Create account" form, which streamlit-authenticator writes back to the same file.

The key that signs the login cookie is a secret and is NOT in config.yaml: anyone who knows it
could make a cookie for any user name and read that user's history. It is read from the
environment variable AUTH_COOKIE_KEY (.env locally, the app's Secrets on Streamlit). Without
it, a random key is made at every start of the server: everything works, but logins are not
remembered after a restart.

The app works without logging in. Logging in adds the history (user_store.py).

Roles: a user whose "roles" in config.yaml include settings.ADMIN_ROLE is the admin
(is_admin()): only the admin may change the knowledge base and save the app settings. Roles
are set by editing config.yaml; accounts created in the app never get one.

Public functions: login_area() (draws the login box), current_user(), is_admin().
"""

import os
import secrets
import time

import streamlit as st
import streamlit_authenticator as stauth
import yaml
from dotenv import load_dotenv
from streamlit_authenticator.utilities import LoginError, Validator

from scanya_ae_afa_updated0209_2_5 import settings

# Seconds to wait after a login or logout before the page is redrawn. The login cookie is
# written (or removed) by a small component in the browser; redrawing at once would remove
# that component before it has done its work, and the login would not survive a page reload.
COOKIE_WAIT_SECONDS = 1.0


# Used when AUTH_COOKIE_KEY is not set. Made once per server process (modules are imported once,
# not at every rerun of the page), so logins hold until the server is restarted.
_RANDOM_COOKIE_KEY = secrets.token_hex(32)


def _cookie_key() -> str:
    """The secret that signs the login cookie: AUTH_COOKIE_KEY, or else the random key above."""
    load_dotenv()
    return os.environ.get("AUTH_COOKIE_KEY", "").strip() or _RANDOM_COOKIE_KEY


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


def is_admin() -> bool:
    """True if the logged-in user has the admin role in config.yaml (False if nobody is logged in).

    Read from the file, not from the login cookie, so removing the role takes effect at once.
    """
    username = current_user()
    if not username or not settings.AUTH_CONFIG_FILE.exists():
        return False
    config = yaml.safe_load(settings.AUTH_CONFIG_FILE.read_text(encoding="utf-8"))
    user = config["credentials"]["usernames"].get(username) or {}
    return settings.ADMIN_ROLE in (user.get("roles") or [])


def login_area() -> str | None:
    """Draw the login / create-account box, or "signed in as" + logout. Returns the username or None.

    streamlit-authenticator keeps the login state in st.session_state ("authentication_status",
    "username", "name"). After logging in or out, the page is redrawn (st.rerun) once the login
    cookie had time to be written or removed.
    """
    authenticator, config = _get_authenticator()
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
            # On the hosted app config.yaml is reset at every restart (it comes from git), so a
            # new account and the way to its history are gone then.
            st.info(
                "Accounts created here only work until the app restarts: the account and its "
                "saved conversations do not persist. For a permanent account, contact the admin.",
                icon=":material/info:",
            )
            try:
                _, new_username, _ = authenticator.register_user(
                    location="main", captcha=False, password_hint=False
                )
                if new_username:
                    _save_config(config)  # The library added the account to config["credentials"].
                    st.success(f"Account **{new_username}** created. You can now log in.")
            except Exception as error:  # e.g. username taken, passwords don't match
                st.error(str(error))
    st.caption("Log in to save your conversations and keep a total cost.")
    if st.session_state.get("authentication_status"):
        time.sleep(COOKIE_WAIT_SECONDS)
        st.rerun()  # just logged in: redraw with the "signed in" line
    return None


def _get_authenticator() -> tuple[stauth.Authenticate, dict]:
    """Return the authenticator for this page run and the content of config.yaml it works on.

    The accounts are passed as a dict, not as the file path: given the path, the library would
    read the cookie key from the file too, and the key must not be in the file. The price: the
    library no longer writes the file itself, so login_area() saves it after a new account
    (_save_config()). Login statistics the library keeps per user (failed attempts, logged in)
    are therefore not written to the file; nothing in the app uses them.
    """
    if not settings.AUTH_CONFIG_FILE.exists():
        _save_config(_starting_config())
    config = yaml.safe_load(settings.AUTH_CONFIG_FILE.read_text(encoding="utf-8"))
    authenticator = stauth.Authenticate(
        config["credentials"],
        cookie_name=config["cookie"]["name"],
        cookie_key=_cookie_key(),
        cookie_expiry_days=config["cookie"]["expiry_days"],
        validator=_AnyPassword(),
        password_instructions="Any password is accepted for now.",  # Help text of the password field.
    )
    return authenticator, config


def _starting_config() -> dict:
    """Content of a new config.yaml: no users yet, name and lifetime of the login cookie."""
    return {
        "credentials": {"usernames": {}},
        "cookie": {"name": "building_rules_login", "expiry_days": 30},
    }


def _save_config(config: dict) -> None:
    """Write the accounts (and cookie name and lifetime) to config.yaml."""
    settings.AUTH_CONFIG_FILE.write_text(yaml.safe_dump(config), encoding="utf-8")
