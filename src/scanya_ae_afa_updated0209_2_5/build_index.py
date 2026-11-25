"""Build the search index from the command line, without opening the app.

Run it from the project folder (or double-click build_index.bat):

    uv run python -m scanya_ae_afa_updated0209_2_5.build_index            update the index
    uv run python -m scanya_ae_afa_updated0209_2_5.build_index --rebuild  embed everything again

Update (the default): files in data/library/<category id>/ that are not in the index yet are
embedded, and documents whose file was deleted are removed from the index. Files already in
the index are left alone, also if their content was changed (see library.py).
Rebuild: the index is deleted and every file is embedded again; needed after changing the
chunk size, the heading rules or the embedding model.

Both show first what they would do and what the embedding will roughly cost, and only go on
after "y". The work itself is done by library.py; this file only prints and asks.
"""

import argparse

from scanya_ae_afa_updated0209_2_5 import library, pricing, settings
from scanya_ae_afa_updated0209_2_5.embeddings import get_embeddings


def main(arguments: list[str] | None = None) -> None:
    """Run the tool. `arguments` replaces the command-line arguments (used by the tests)."""
    parser = argparse.ArgumentParser(description="Update or rebuild the search index from data/library/.")
    parser.add_argument("--rebuild", action="store_true", help="delete the index and embed every file again")
    options = parser.parse_args(arguments)

    # 1. Say what will happen.
    if options.rebuild:
        to_embed, removed = library.library_files(), []
        print(f"Rebuild: the index is deleted and all {len(to_embed)} file(s) are embedded again.")
    else:
        to_embed, removed = library.pending_changes()
        if not to_embed and not removed:
            print("The index is up to date: no new files, no deleted files.")
            return
        for category_id, path in to_embed:
            print(f"  new:     {category_id} / {path.name}")
        for document in removed:
            print(f"  deleted: {document['category']} / {document['source']}")
    tokens = library.estimate_tokens(to_embed)
    estimate = pricing.format_usd(tokens * settings.EMBEDDING_PRICE_PER_MILLION_TOKENS / 1_000_000, markdown=False)
    print(f"To embed: {len(to_embed)} file(s), about {tokens:,} tokens, about {estimate}.")

    # 2. Ask.
    if input("Go on? [y/N] ").strip().lower() != "y":
        print("Nothing was changed.")
        return

    # 3. Do it, and report.
    embeddings = get_embeddings()  # Notes its requests, for the cost printed at the end.
    if options.rebuild:
        added, problems = library.rebuild_index(embeddings)
        print(f"{added} document(s) indexed.")
    else:
        added, removed_count, problems = library.sync_index(embeddings)
        print(f"{added} document(s) added, {removed_count} removed.")
    for problem in problems:
        print(f"  problem: {problem}")
    if any("API_KEY" in problem for problem in problems):  # config.py could not find the key.
        print("The API key was not found. Set OPENROUTER_API_KEY as an environment variable or in .env.")
    usage = {}
    for request in embeddings.usage:
        pricing.add_request(usage, **request)
    cost = pricing.format_usd(pricing.total_cost(usage), markdown=False)
    print(f"Embedding: {pricing.total_tokens(usage):,} tokens, {cost}.")


if __name__ == "__main__":
    main()
