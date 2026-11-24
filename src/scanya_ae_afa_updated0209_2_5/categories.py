"""Document categories: read from categories.toml in the project root.

A category groups documents (e.g. "Fire safety"). Its id is stored with every chunk in the
index, which is what lets a conversation search only the categories that are switched on.

Public: Category, load_categories().
"""

import re
import tomllib
from dataclasses import dataclass

from scanya_ae_afa_updated0209_2_5 import settings

# Ids end up in folder names and in search filters, so only safe characters are allowed.
_ID_PATTERN = re.compile(r"[a-z0-9_]+")


@dataclass(frozen=True)
class Category:
    """One document category, as defined in categories.toml."""

    id: str
    name: str
    description: str = ""


def load_categories() -> list[Category]:
    """Return the categories from categories.toml, in file order.

    Raises:
        ValueError: if the file has no categories, or an id is invalid or used twice.
    """
    with open(settings.CATEGORIES_FILE, "rb") as file:
        entries = tomllib.load(file).get("category", [])
    categories = [Category(entry["id"], entry["name"], entry.get("description", "")) for entry in entries]
    if not categories:
        raise ValueError(f"No categories defined in {settings.CATEGORIES_FILE.name}.")
    seen = set()
    for category in categories:
        if not _ID_PATTERN.fullmatch(category.id):
            raise ValueError(f"Invalid category id '{category.id}': use lowercase letters, digits and '_' only.")
        if category.id in seen:
            raise ValueError(f"Category id '{category.id}' is defined twice.")
        seen.add(category.id)
    return categories
