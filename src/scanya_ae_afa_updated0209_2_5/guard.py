"""Prompt-injection guard: a small, cheap model checks each question before the chat agent runs (no Streamlit code).

Idea (adapted from guard.py of the Sprint 1 project): the user's question is judged by
settings.GUARD_MODEL before it reaches the chat model the user chose. Only a question that
is allowed goes on to the agent; a blocked one costs one small request instead of a full
answer with searches.

What is blocked (the rules are in prompts.GUARD_SYSTEM_PROMPT):
- prompt injection: attempts to change the assistant's rules or role, to reveal its
  instructions, or to slip in hidden instructions;
- requests outside the domain (building regulations, architecture, the user's project);
- requests for harmful help, such as forging certificates or deceiving the authorities.
Follow-ups ("and for hotels?"), greetings and requests to change the work product are allowed.
To judge a follow-up, the guard also sees the start of the assistant's last answer.

The model answers with structured output (GuardVerdict), so the code reads a yes/no instead
of parsing free text.

Fail closed: if the guard model cannot be reached, the error is raised and the question is not
answered (the page shows the error). If it answers without a readable verdict, the question is
blocked. A guard that silently lets questions through when it fails would not protect anything.

What it does not check: the project input and the knowledge-base documents. They are long and
sent with every question, so checking them each time would cost much more; the system prompt
declares them material, never instructions (prompts.SYSTEM_PROMPT).

Public: GuardResult, check_question().
"""

from dataclasses import dataclass, field

from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, Field

from scanya_ae_afa_updated0209_2_5 import config, prompts, settings


class GuardVerdict(BaseModel):
    """What the guard model must answer (structured output)."""

    allowed: bool = Field(description="True if the message may be passed on to the assistant.")
    reason: str = Field(description="If not allowed: one short sentence for the user, in the language asked for.")


@dataclass(frozen=True)
class GuardResult:
    """Result of check_question().

    allowed: True if the question may go on to the chat agent.
    reason:  if not allowed, the guard's one sentence for the user, in the language asked for;
             "" if allowed, or if the model gave no readable verdict (the page then shows its
             own message, translations.py "guard_no_verdict").
    usage:   the guard's request, with the keys of pricing.add_request(); {} if the model
             reported no token counts.
    """

    allowed: bool
    reason: str = ""
    usage: dict = field(default_factory=dict)


def check_question(
    question: str,
    history: list[dict],
    guard_model: BaseChatModel | None = None,
    language: str = "English",
) -> GuardResult:
    """Ask the guard model whether `question` may be passed on to the chat agent.

    Args:
        question: The user's new message (already checked by agent.validate_question()).
        history: Earlier messages of the conversation ({"role", "content"} dicts, oldest
            first); only the start of the last assistant answer is shown to the guard.
        guard_model: Only for tests, to run without an API key.
        language: Language of the reason, in English ("Catalan"): the language of the interface.

    Raises:
        Whatever the model API raises (missing key, network ...): fail closed, see above.
    """
    model = guard_model or config.get_chat_model(settings.GUARD_MODEL, temperature=0.0)
    # include_raw=True also returns the raw AIMessage, which carries the token counts and cost.
    checker = model.with_structured_output(GuardVerdict, include_raw=True)

    last_answer = next((m["content"] for m in reversed(history) if m["role"] == "assistant"), "")
    user_prompt = prompts.GUARD_USER_PROMPT.format(
        last_answer=last_answer[: settings.GUARD_CONTEXT_CHARS] or "(none, this is the first message)",
        question=question,
        language=language,
    )
    result = checker.invoke([("system", prompts.GUARD_SYSTEM_PROMPT), ("user", user_prompt)])

    raw, verdict = result["raw"], result["parsed"]
    usage = {}
    if getattr(raw, "usage_metadata", None):
        usage = {
            "model": settings.GUARD_MODEL,
            "input_tokens": raw.usage_metadata["input_tokens"],
            "output_tokens": raw.usage_metadata["output_tokens"],
            "reported_cost": raw.response_metadata.get("cost"),
        }

    if verdict is None:  # The model answered, but not in the required format.
        return GuardResult(False, "", usage)
    if not verdict.allowed:
        return GuardResult(False, verdict.reason.strip(), usage)
    return GuardResult(True, "", usage)
