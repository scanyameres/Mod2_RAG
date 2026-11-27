"""Small flow diagram of how an answer is made, shown above the output (no Streamlit code).

    You → Guard → Model ⇄ Knowledge base
                        → Work product
                        → Answer

While an answer runs, page_chat.py redraws the diagram after every event of
agent.answer_question(): the step that is running now pulses, the steps already done are
tinted. The agent reports a step when it has finished, so next_stage() works out which step
runs next:

- the guard runs first (if switched on); its first event means it is done, the model starts;
- a tool call starts the tool: search_documentation and read_passages read the knowledge
  base (RAG), write_document writes the work product;
- a tool result hands back to the model;
- the answer ends the run.

A tool step usually lasts a fraction of a second, against seconds for the model, so its box
would only flash. A step that has just ended therefore keeps an afterglow: it starts in the
running colour and fades to the "done" tint in AFTERGLOW_SECONDS, while the next step already
pulses. The browser plays the fade (CSS), so the answer is not delayed. page_chat.py notes when
each step ended and passes the seconds since then (`fading`); every redraw starts the fade that
far in (negative animation-delay), so a redraw continues a fade instead of restarting it.

The diagram is also the key of the app's colour code (COLOURS): every step has the colour of
the controls and views that change or show it, e.g. the Model box is blue like the model
settings below the chat and the Search steps view. app.py tints those with the same values.

The texts of the boxes and of the status box are in translations.py (keys "node_<stage>",
"node_<stage>_sub" and "stage_<stage>"), so the diagram is drawn in the user's language.

Public: COLOURS, CATEGORY_SHADES, category_colours(), STAGES_WITH_LABEL, AFTERGLOW_SECONDS, stage_label(),
next_stage(), diagram_html().
"""

from scanya_ae_afa_updated0209_2_5 import translations

# The colour code of the app, as "R, G, B" for see-through rgba() colours (they work in light
# and dark mode). 47, 111, 98 is the app's primary colour #2F6F62 (.streamlit/config.toml).
COLOURS = {
    "knowledge": "47, 111, 98",  # Knowledge base: documents to search, hybrid search, References.
    "model": "52, 120, 190",  # Model: model, passages and searches settings, Search steps.
    "output": "196, 140, 60",  # Work product.
    "neutral": "120, 120, 120",  # You, Guard, Answer: the question field and the chat.
}

# Shades of green for the document types (categories.toml), given in file order. Everything
# about the knowledge base as a whole uses COLOURS["knowledge"] (the app's teal green: the
# Documents to search box, hybrid search, the References view, the "cited" marks); these
# greens only mark one document type: its switch in the sidebar, its references, its box on
# the Knowledge base page. Dark to light, so the first (most general) type is the darkest.
CATEGORY_SHADES = ("34, 102, 45", "76, 150, 60", "140, 180, 50")


def category_colours(category_ids: list[str]) -> dict[str, str]:
    """Category id -> its shade ("R, G, B"), by position; more types than shades reuse them."""
    return {category_id: CATEGORY_SHADES[index % len(CATEGORY_SHADES)] for index, category_id in enumerate(category_ids)}

# The stages that have a text for the status box in the chat while they run (stage_label()).
STAGES_WITH_LABEL = ("guard", "model", "search", "write", "answer")

# How long a step that has just ended takes to fade from the running colour to "done".
AFTERGLOW_SECONDS = 1.5

# Tool name (agent.py) -> stage of the diagram.
_TOOL_STAGES = {"search_documentation": "search", "read_passages": "search", "write_document": "write"}


# Stage id -> its colour in COLOURS; the stages not listed are "neutral".
_NODE_COLOURS = {"model": "model", "search": "knowledge", "write": "output"}

# The look of the diagram. Each box gets its colour as the CSS variable --rgb (diagram_html()):
# light at rest, stronger once done, solid and pulsing while it runs, fading after it ended
# (.recent; its duration and delay are set per box in diagram_html()).
_CSS = """
<style>
.flow { display: flex; align-items: center; gap: 0.35rem; font-size: 0.8rem; margin-bottom: 0.25rem; }
.flow-node { flex: 1; min-width: 0; text-align: center; line-height: 1.15; padding: 0.3rem 0.4rem;
  border: 1px solid rgba(var(--rgb), 0.45); border-radius: 0.5rem; background: rgba(var(--rgb), 0.1);
  transition: background 0.3s, border-color 0.3s; }
.flow-node small { display: block; opacity: 0.65; font-size: 0.68rem; }
.flow-node.done { background: rgba(var(--rgb), 0.24); border-color: rgba(var(--rgb), 0.8); }
.flow-node.active { background: rgb(var(--rgb)); border-color: rgb(var(--rgb)); color: #fff;
  animation: flow-pulse 1.2s ease-in-out infinite; }
.flow-node.recent { animation-name: flow-afterglow; animation-timing-function: ease-in; }
.flow-node.off { opacity: 0.4; text-decoration: line-through; }
.flow-stack { flex: 1.6; display: flex; flex-direction: column; gap: 0.15rem; }
.flow-stack .flow-node { padding: 0.1rem 0.4rem; white-space: nowrap; }
.flow-stack .flow-node small { display: inline; margin-left: 0.3rem; }
.flow-arrow { opacity: 0.5; }
/* In a narrow window only the titles are shown, so the boxes stay on one line. */
@media (max-width: 1250px) { .flow-node small, .flow-stack .flow-node small { display: none; } }
@keyframes flow-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(var(--rgb), 0.55); }
  50% { box-shadow: 0 0 0 0.35rem rgba(var(--rgb), 0); }
}
@keyframes flow-afterglow {
  from { background: rgb(var(--rgb)); border-color: rgb(var(--rgb)); color: #fff; }
  to { background: rgba(var(--rgb), 0.24); border-color: rgba(var(--rgb), 0.8); color: inherit; }
}
</style>
"""


def stage_label(stage: str, language: str = translations.DEFAULT_LANGUAGE) -> str:
    """Text of the chat's status box while `stage` (one of STAGES_WITH_LABEL) runs, e.g. "Thinking…"."""
    return translations.text(f"stage_{stage}", language)


def next_stage(current: str, kind: str, tool: str = "") -> str:
    """The stage that runs after an event of `kind` (and `tool`) arrived during stage `current`.

    Stages: "guard", "model", "search", "write", "answer", or "end" (blocked by the guard).
    """
    if kind == "blocked":
        return "end"
    if kind == "answer":
        return "answer"
    if kind == "tool_call":
        return _TOOL_STAGES.get(tool, "model")
    if kind == "tool_result":
        return "model"
    # A usage event: the guard's request ends the guard; any other request changes nothing.
    return "model" if current == "guard" else current


def diagram_html(
    active: str | None = None,
    done: set[str] = frozenset(),
    guard_on: bool = True,
    language: str = translations.DEFAULT_LANGUAGE,
    fading: dict[str, float] | None = None,
) -> str:
    """HTML of the diagram: `active` pulses, the stages in `done` are tinted more, the guard is struck out if off.

    `fading`: stage -> seconds since it ended. A done stage ended less than AFTERGLOW_SECONDS
    ago still fades out (afterglow), from the point it has reached.
    """
    fading = fading or {}

    def node(stage: str) -> str:
        title = translations.text(f"node_{stage}", language)
        subtitle = translations.text(f"node_{stage}_sub", language)
        classes = ["flow-node"]
        style = f"--rgb: {COLOURS[_NODE_COLOURS.get(stage, 'neutral')]}"
        if stage == active:
            classes.append("active")
        elif stage in done:
            classes.append("done")
            elapsed = fading.get(stage, AFTERGLOW_SECONDS)
            if elapsed < AFTERGLOW_SECONDS:
                classes.append("recent")
                # A negative delay starts the fade `elapsed` seconds in, so a redraw continues it.
                style += f"; animation-duration: {AFTERGLOW_SECONDS}s; animation-delay: -{elapsed:.2f}s"
        if stage == "guard" and not guard_on:
            classes.append("off")
        return f'<div style="{style}" class="{" ".join(classes)}"><b>{title}</b><small>{subtitle}</small></div>'

    arrow = '<span class="flow-arrow">→</span>'
    return (
        _CSS
        + '<div class="flow">'
        + node("you") + arrow + node("guard") + arrow + node("model")
        + '<span class="flow-arrow">⇄</span>'
        + '<div class="flow-stack">' + node("search") + node("write") + node("answer") + "</div>"
        + "</div>"
    )
