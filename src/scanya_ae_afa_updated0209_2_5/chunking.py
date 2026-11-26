"""Turn an uploaded file into text chunks (no API calls, no database).

read_pages() extracts the text (PDF: one text per page; .txt/.md: the whole file).
split_pages() cuts it into overlapping chunks. Every chunk remembers:
- its page number, and
- its section: the headings above it, e.g. "4 Bäder › 4.2 Lüftung" or "Art. 6 Abstandsflächen",
so a reference can say where in the document a passage is, not only on which page.

Headings are recognised from the text itself with cautious rules (see _read_heading()). A
document without recognisable headings simply gets chunks with an empty section.

Public: Chunk, read_pages(), split_pages().
"""

import io
import re
from dataclasses import dataclass
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from scanya_ae_afa_updated0209_2_5 import settings

SECTION_SEPARATOR = " › "  # Between the levels of a section, e.g. "4 Bäder › 4.2 Lüftung".
_MAX_HEADING_LENGTH = 90  # Longer lines are sentences, not headings.
_MAX_NUMBERED_TITLE_WORDS = 8  # "4.2 Lüftung" is a heading; a numbered sentence has more words.

# --- Heading patterns. Each gives a level: a new heading closes all headings of the same or
# a deeper level, so the section is always the path from the top-level heading down. ---

# Markdown: "## Title" (level = number of #).
_MARKDOWN = re.compile(r"^(#{1,6})\s+(\S.*?)\s*#*$")
# Legal structure words followed by a number, e.g. "Teil 2", "Abschnitt III", "§ 14", "Art. 6".
_LEGAL_LEVELS = (
    (1, r"Teil|Part|Buch|Titel|Anhang|Anlage|Annex|Appendix"),
    (2, r"Kapitel|Chapter"),
    (3, r"Abschnitt|Section"),
    (4, r"Unterabschnitt|Subsection"),
    (5, r"§+|Art\.|Artikel|Article"),
)
_LEGAL = [
    (level, re.compile(rf"^({words})\s*(\d+\s?[a-z]?|[IVXLC]+|[A-Z])\b[.:]?\s*(.*)$"))
    for level, words in _LEGAL_LEVELS
]
# German laws also write "Erster Teil", "Zweiter Abschnitt".
_ORDINAL = re.compile(
    r"^(Erster|Zweiter|Dritter|Vierter|Fünfter|Sechster|Siebe?n?ter|Achter|Neunter|Zehnter)\s+"
    r"(Teil|Kapitel|Abschnitt|Unterabschnitt)\b[.:]?\s*(.*)$"
)
_ORDINAL_LEVELS = {"Teil": 1, "Kapitel": 2, "Abschnitt": 3, "Unterabschnitt": 4}
# Numbered headings: "4.2 Lüftung", "4.2.3 Fensterlose Bäder" (level 10 + number of parts).
_NUMBERED = re.compile(r"^([1-9]\d?(?:\.\d{1,2}){1,4})\.?\s+([A-ZÄÖÜ].*)$")
# Top-level numbered heading: "4 Bäder" or "4. Bäder". Only accepted in sequence (see below).
_TOP_NUMBERED = re.compile(r"^([1-9]\d?)\.?\s+([A-ZÄÖÜ]\D*)$")
# A line that starts like "§ 14 Abs. 2 ..." is a reference inside a sentence, not a heading.
_REFERENCE_WORDS = re.compile(r"^(Abs|Absatz|Satz|Nr|Nummer|bis|und|oder|of|and|or|to)\b|^[,(]")
# Dots and page number at the end of a table-of-contents line: "4.2 Lüftung ........ 17".
_CONTENTS_LEADER = re.compile(r"[\s.·…]{3,}\d+\s*$")


@dataclass(frozen=True)
class Chunk:
    """A piece of a document.

    `page` is the 1-based PDF page, or None for text files. `section` is the path of headings
    above the chunk, joined with SECTION_SEPARATOR, or "" if no heading was recognised.
    """

    text: str
    page: int | None
    section: str = ""


def read_pages(file_name: str, data: bytes) -> list[tuple[int | None, str]]:
    """Extract the text of a file as (page number, text) pairs; empty pages are skipped.

    Raises:
        ValueError: file larger than MAX_UPLOAD_MB, unsupported file type, unreadable file,
            or no text found (e.g. a scanned PDF, which only contains images).
    """
    if len(data) > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise ValueError(f"The file is larger than {settings.MAX_UPLOAD_MB} MB.")
    extension = Path(file_name).suffix.lower()
    if extension == ".pdf":
        try:
            reader = PdfReader(io.BytesIO(data))
            pages = [(number, page.extract_text() or "") for number, page in enumerate(reader.pages, start=1)]
        except Exception as error:  # pypdf raises many different errors for broken files.
            raise ValueError(f"Could not read the PDF: {error}") from error
    elif extension in (".txt", ".md"):
        pages = [(None, data.decode("utf-8", errors="replace"))]
    else:
        raise ValueError(f"Unsupported file type '{extension}'. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}.")

    pages = [(number, text) for number, text in pages if text.strip()]
    if not pages:
        raise ValueError("No text found in the file. Scanned PDFs (images of pages) are not supported.")
    return pages


def _looks_like_title(text: str, max_words: int | None = None) -> bool:
    """True for a short line that does not end like a sentence."""
    if max_words and len(text.split()) > max_words:
        return False
    return 0 < len(text) <= _MAX_HEADING_LENGTH and not text.endswith((".", ";", ","))


class _SectionTracker:
    """Follows the headings while a document is read line by line."""

    def __init__(self) -> None:
        self._open: list[tuple[int, str]] = []  # (level, title) from the top level down.
        self._last_top_number = 0  # First number of the latest numbered heading ("4 ..." or "4.2 ...").

    @property
    def section(self) -> str:
        """The current section: the titles of all open headings, top level first."""
        return SECTION_SEPARATOR.join(title for _, title in self._open)

    def read_heading(self, lines: list[str], index: int) -> int:
        """If lines[index] is a heading, make it the current section.

        Returns the number of lines the heading takes: 0 (not a heading), 1, or 2 when the
        title stands on the next line ("§ 14" / "Brandschutz").
        """
        next_line = _clean(lines[index + 1]) if index + 1 < len(lines) else ""
        found = self._match(_clean(lines[index]), next_line)
        if found is None:
            return 0
        level, title, title_may_follow, top_number = found
        used = 1
        if title_may_follow and _looks_like_title(next_line) and next_line[0].isupper() and self._match(next_line) is None:
            # Legal headings often put the title on its own line below the number.
            title, used = f"{title} {next_line}", 2
        if top_number:
            self._last_top_number = top_number
        while self._open and self._open[-1][0] >= level:
            self._open.pop()
        self._open.append((level, title))
        return used

    def _match(self, line: str, next_line: str = "") -> tuple[int, str, bool, int | None] | None:
        """Check one line against the heading patterns (changes nothing).

        Returns (level, title, the title may follow on the next line, top-level number of a
        numbered heading or None), or None if the line is not a heading.
        """
        if not line or len(line) > _MAX_HEADING_LENGTH:
            return None
        if match := _MARKDOWN.match(line):
            return len(match.group(1)), match.group(2), False, None
        if match := _ORDINAL.match(line):
            if _looks_like_title(line):
                return _ORDINAL_LEVELS[match.group(2)], line, not match.group(3), None
            return None
        for level, pattern in _LEGAL:
            if match := pattern.match(line):
                rest = match.group(3)
                if _REFERENCE_WORDS.match(rest) or (rest and not _looks_like_title(rest)):
                    return None  # "§ 14 Abs. 2 gilt entsprechend." is a sentence.
                return level, line, not rest, None
        if match := _NUMBERED.match(line):
            if _looks_like_title(match.group(2), _MAX_NUMBERED_TITLE_WORDS):
                number = match.group(1)
                return 10 + number.count(".") + 1, line, False, int(number.split(".")[0])
            return None  # A numbered sentence ("4.2.1 Fensterlose Bäder müssen ...") stays text.
        if match := _TOP_NUMBERED.match(line):
            # "3 Stellplätze" could be plain text. Accept a single number only if the title has
            # no digits (table rows do) and the number fits: it continues the numbering (1,
            # then 2, then 3 ...), or its first sub-heading follows ("4 Bäder" / "4.1 ...").
            number = int(match.group(1))
            in_sequence = number in (1, self._last_top_number + 1)
            sub_heading = _NUMBERED.match(next_line)
            has_sub_heading = bool(sub_heading) and sub_heading.group(1).split(".")[0] == str(number)
            if (in_sequence or has_sub_heading) and _looks_like_title(match.group(2), _MAX_NUMBERED_TITLE_WORDS):
                return 11, line, False, number
        return None


def _clean(line: str) -> str:
    """Collapse spaces and drop the dots and page number of a table-of-contents line."""
    return _CONTENTS_LEADER.sub("", " ".join(line.split()))


def split_pages(pages: list[tuple[int | None, str]]) -> list[Chunk]:
    """Split the pages into chunks of about CHUNK_SIZE characters, overlapping by CHUNK_OVERLAP.

    A chunk never spans two pages (so its page number is exact) and never spans two sections:
    the text is first cut at every recognised heading, then each part is split by size. The
    splitter prefers to cut at paragraph, then line, then sentence boundaries.
    """
    splitter = RecursiveCharacterTextSplitter(chunk_size=settings.CHUNK_SIZE, chunk_overlap=settings.CHUNK_OVERLAP)
    tracker = _SectionTracker()
    chunks: list[Chunk] = []

    def add_part(lines: list[str], page_number: int | None, section: str) -> None:
        chunks.extend(Chunk(text, page_number, section) for text in splitter.split_text("\n".join(lines)))

    for page_number, page_text in pages:
        lines = page_text.splitlines()
        part: list[str] = []  # Lines of the current section on this page.
        part_section = tracker.section
        has_body = False  # Whether `part` holds more than heading lines.
        index = 0
        while index < len(lines):
            heading_lines = tracker.read_heading(lines, index)
            if heading_lines:
                if has_body:  # A new section starts: finish the previous one.
                    add_part(part, page_number, part_section)
                    part, has_body = [], False
                # Headings directly below each other (chapter, then article) open one part.
                part_section = tracker.section
                part.extend(lines[index : index + heading_lines])
                index += heading_lines
            else:
                part.append(lines[index])
                has_body = has_body or bool(lines[index].strip())
                index += 1
        if has_body:  # A heading at the very end of a page has no text here: nothing to add.
            add_part(part, page_number, part_section)
    return chunks
