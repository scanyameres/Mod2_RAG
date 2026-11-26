"""Command-line tool: set the password of an account in config.yaml.

Used for the admin account, whose password must not be one of the demo passwords in the
README. The password is typed in hidden, stored as a bcrypt hash (as the login library does)
and never shown. Run locally, then commit config.yaml and push: on the hosted app, changes
to config.yaml are lost at the next restart.

    uv run python -m scanya_ae_afa_updated0209_2_5.set_password sergi
"""

import getpass
import sys

import yaml
from streamlit_authenticator.utilities.hasher import Hasher

from scanya_ae_afa_updated0209_2_5 import settings


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Usage: uv run python -m scanya_ae_afa_updated0209_2_5.set_password <username>")
    username = sys.argv[1].strip().lower()
    config = yaml.safe_load(settings.AUTH_CONFIG_FILE.read_text(encoding="utf-8"))
    users = config["credentials"]["usernames"]
    if username not in users:
        sys.exit(f"No account '{username}' in {settings.AUTH_CONFIG_FILE.name}.")

    password = getpass.getpass(f"New password for {username}: ")
    if len(password) < 8:
        sys.exit("Not changed: use at least 8 characters.")
    if password != getpass.getpass("Repeat it: "):
        sys.exit("Not changed: the two passwords differ.")

    users[username]["password"] = Hasher.hash(password)
    settings.AUTH_CONFIG_FILE.write_text(yaml.safe_dump(config), encoding="utf-8")
    print(f"Password of {username} changed in {settings.AUTH_CONFIG_FILE.name}. Commit and push it.")


if __name__ == "__main__":
    main()
