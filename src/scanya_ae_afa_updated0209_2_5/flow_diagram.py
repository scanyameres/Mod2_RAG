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

The diagram is also the key of the app's colour code (COLOURS): every step has the colour of
the controls and views that change or show it, e.g. the Model box is blue like the model
settings below the chat and the Search steps view. app.py tints those with the same values.

Public: COLOURS, STAGE_LABELS, next_stage(), diagram_html().
"""

# The colour code of the app, as "R, G, B" for see-through rgba() colours (they work in light
# and dark mode). 47, 111, 98 is the app's primary colour #2F6F62 (.streamlit/config.toml).
COLOURS = {
    "knowledge": "47, 111, 98",  # Knowledge base: documents to search, hybrid search, References.
    "model": "52, 120, 190",  # Model: model, passages and searches settings, Search steps.
    "output": "196, 140, 60",  # Work product.
    "neutral": "120, 120, 120",  # You, Guard, Answer: the question field and the chat.
}

# Stage id -> text of the status box in the chat while that stage runs.
STAGE_LABELS = {
    "guard": "Checking the question…",
    "model": "Thinking…",
    "search": "Reading the knowledge base…",
    "write": "Writing the work product…",
    "answer": "Answering…",
}

# Tool name (agent.py) -> stage of the diagram.
_TOOL_STAGES = {"search_documentation": "search", "read_passages": "search", "write_document": "write"}

# Stage id -> (title, subtitle) of its box.
_NODES = {
    "you": ("You", "question"),
    "guard": ("Guard", "safety check"),
    "model": ("Model", "LLM"),
    "search": ("Knowledge base", "RAG search"),
    "write": ("Work product", "tool"),
    "answer": ("Answer", "chat"),
}

# Stage id -> its colour in COLOURS; the stages not listed are "neutral".
_NODE_COLOURS = {"model": "model", "search": "knowledge", "write": "output"}

# The look of the diagram. Each box gets its colour as the CSS variable --rgb (diagram_html()):
# light at rest, stronger once done, solid and pulsing while it runs.
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
</style>
"""


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


def diagram_html(active: str | None = None, done: set[str] = frozenset(), guard_on: bool = True) -> str:
    """HTML of the diagram: `active` pulses, the stages in `done` are tinted more, the guard is struck out if off."""

    def node(stage: str) -> str:
        title, subtitle = _NODES[stage]
        classes = ["flow-node"]
        if stage == active:
            classes.append("active")
        elif stage in done:
            classes.append("done")
        if stage == "guard" and not guard_on:
            classes.append("off")
        colour = COLOURS[_NODE_COLOURS.get(stage, "neutral")]
        return f'<div style="--rgb: {colour}" class="{" ".join(classes)}"><b>{title}</b><small>{subtitle}</small></div>'

    arrow = '<span class="flow-arrow">→</span>'
    return (
        _CSS
        + '<div class="flow">'
        + node("you") + arrow + node("guard") + arrow + node("model")
        + '<span class="flow-arrow">⇄</span>'
        + '<div class="flow-stack">' + node("search") + node("write") + node("answer") + "</div>"
        + "</div>"
    )
