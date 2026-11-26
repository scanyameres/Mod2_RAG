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

Public: STAGE_LABELS, next_stage(), diagram_html().
"""

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

# The look of the diagram. Colours are see-through, so they work in light and dark mode;
# #2F6F62 is the app's primary colour (.streamlit/config.toml).
_CSS = """
<style>
.flow { display: flex; align-items: center; gap: 0.35rem; font-size: 0.8rem; margin-bottom: 0.25rem; }
.flow-node { flex: 1; min-width: 0; text-align: center; line-height: 1.15; padding: 0.3rem 0.4rem;
  border: 1px solid rgba(128, 128, 128, 0.35); border-radius: 0.5rem; background: rgba(128, 128, 128, 0.06);
  transition: background 0.3s, border-color 0.3s; }
.flow-node small { display: block; opacity: 0.65; font-size: 0.68rem; }
.flow-node.done { background: rgba(47, 111, 98, 0.14); border-color: rgba(47, 111, 98, 0.5); }
.flow-node.active { background: #2F6F62; border-color: #2F6F62; color: #fff;
  animation: flow-pulse 1.2s ease-in-out infinite; }
.flow-node.off { opacity: 0.4; text-decoration: line-through; }
.flow-stack { flex: 1.6; display: flex; flex-direction: column; gap: 0.15rem; }
.flow-stack .flow-node { padding: 0.1rem 0.4rem; white-space: nowrap; }
.flow-stack .flow-node small { display: inline; margin-left: 0.3rem; }
.flow-arrow { opacity: 0.5; }
/* In a narrow window only the titles are shown, so the boxes stay on one line. */
@media (max-width: 1250px) { .flow-node small, .flow-stack .flow-node small { display: none; } }
@keyframes flow-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(47, 111, 98, 0.55); }
  50% { box-shadow: 0 0 0 0.35rem rgba(47, 111, 98, 0); }
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
    """HTML of the diagram: `active` pulses, the stages in `done` are tinted, the guard is struck out if off."""

    def node(stage: str) -> str:
        title, subtitle = _NODES[stage]
        classes = ["flow-node"]
        if stage == active:
            classes.append("active")
        elif stage in done:
            classes.append("done")
        if stage == "guard" and not guard_on:
            classes.append("off")
        return f'<div class="{" ".join(classes)}"><b>{title}</b><small>{subtitle}</small></div>'

    arrow = '<span class="flow-arrow">→</span>'
    return (
        _CSS
        + '<div class="flow">'
        + node("you") + arrow + node("guard") + arrow + node("model")
        + '<span class="flow-arrow">⇄</span>'
        + '<div class="flow-stack">' + node("search") + node("write") + node("answer") + "</div>"
        + "</div>"
    )
