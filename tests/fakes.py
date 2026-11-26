"""Fake models shared by the tests, so they run without an API key."""

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda


class FakeGuardModel:
    """Stands in for the guard model of guard.py: always gives the same verdict.

    Supports only what guard.check_question() uses: with_structured_output(schema,
    include_raw=True), whose result is {"raw": AIMessage, "parsed": verdict, "parsing_error": None}.
    `allowed=None` simulates a reply without a readable verdict. The prompts it received are
    kept in `received`, so a test can look at them.
    """

    def __init__(self, allowed: bool | None = True, reason: str = "", usage_metadata: dict | None = None):
        self.allowed, self.reason, self.usage_metadata = allowed, reason, usage_metadata
        self.received = []

    def with_structured_output(self, schema, include_raw=False, **kwargs):
        def reply(messages):
            self.received.append(messages)
            parsed = None if self.allowed is None else schema(allowed=self.allowed, reason=self.reason)
            return {"raw": AIMessage(content="", usage_metadata=self.usage_metadata), "parsed": parsed, "parsing_error": None}

        return RunnableLambda(reply)
