"""The workspace of one conversation: everything the assistant works with besides the chat
messages (no Streamlit code, no API calls).

- Project input: the user's own files (drafts, requirement lists) and notes. They describe
  the project the conversation is about. Their text is sent to the chat model with every
  question; they are NOT added to the knowledge base.
- Work product: a Markdown document the assistant writes and revises on request (a list of
  applicable rules, a checklist, a report ...), shown next to the chat.
- Sources: every knowledge-base passage found in this conversation, each with a fixed
  number. "[3]" means the same passage in every answer and in the work product.

Public: Workspace, citation_numbers().
"""

import re
from dataclasses import asdict, dataclass, field

from scanya_ae_afa_updated0209_2_5 import chunking, settings
from scanya_ae_afa_updated0209_2_5.retrieval import Hit

# Citations look like [1] or [2, 5].
_CITATION = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")


def citation_numbers(text: str) -> list[int]:
    """Return the passage numbers cited in `text`, each once, in order of first appearance."""
    numbers = []
    for match in _CITATION.finditer(text):
        for number in map(int, re.findall(r"\d+", match.group(1))):
            if number not in numbers:
                numbers.append(number)
    return numbers


@dataclass
class Workspace:
    """State of one conversation besides its messages. The app keeps one per conversation."""

    project_files: dict[str, str] = field(default_factory=dict)  # File name -> extracted text.
    project_notes: str = ""
    document_title: str = ""
    document: str = ""  # The work product (Markdown); empty until the assistant writes one.
    sources: dict[str, dict] = field(default_factory=dict)  # Chunk id -> source (see add_source).

    # --- Project input ---

    def add_project_file(self, file_name: str, data: bytes) -> None:
        """Read a project file (PDF, TXT, MD) and keep its text. Same name = replaced.

        Raises:
            ValueError: file too large, unsupported type, or no readable text (scanned PDF).
        """
        pages = chunking.read_pages(file_name, data)
        self.project_files[file_name] = "\n\n".join(text.strip() for _, text in pages)

    def project_input(self) -> str:
        """Return the notes and file texts as one text for the chat model ("" if there are none).

        Cut after MAX_PROJECT_INPUT_CHARS characters, with a remark, because it is sent with
        every question (see project_input_is_cut()).
        """
        parts = []
        if self.project_notes.strip():
            parts.append(f"Notes from the user:\n{self.project_notes.strip()}")
        parts.extend(f"File: {name}\n{text}" for name, text in self.project_files.items())
        text = "\n\n---\n\n".join(parts)
        if len(text) > settings.MAX_PROJECT_INPUT_CHARS:
            text = text[: settings.MAX_PROJECT_INPUT_CHARS] + "\n[... the rest of the project input was cut: too long]"
        return text

    def project_input_is_cut(self) -> bool:
        """True if the project input is longer than the limit, so the model sees only its start."""
        return len(self.project_notes) + sum(map(len, self.project_files.values())) > settings.MAX_PROJECT_INPUT_CHARS

    # --- Sources ---

    def add_source(self, hit: Hit) -> dict:
        """Register a found passage and return it as a dict: the Hit fields plus "number".

        A passage found again keeps its number, but takes the ranks of the latest search.
        """
        number = self.sources[hit.chunk_id]["number"] if hit.chunk_id in self.sources else len(self.sources) + 1
        self.sources[hit.chunk_id] = {"number": number, **asdict(hit)}
        return self.sources[hit.chunk_id]

    def sources_by_number(self, numbers: list[int] | None = None) -> list[dict]:
        """Return the sources sorted by number; only those in `numbers` if given."""
        sources = sorted(self.sources.values(), key=lambda source: source["number"])
        return [source for source in sources if numbers is None or source["number"] in numbers]

    # --- Work product ---

    def export_document(self) -> str:
        """Return the work product as Markdown, with a list of the references it cites."""
        cited = self.sources_by_number(citation_numbers(self.document))
        text = f"# {self.document_title}\n\n{self.document}\n"
        if cited:
            lines = [
                f"- [{source['number']}] {source['source']}"
                + (f", {source['section']}" if source["section"] else "")
                + (f", page {source['page']}" if source["page"] else "")
                for source in cited
            ]
            text += "\n## References\n\n" + "\n".join(lines) + "\n"
        return text
