"""Costs of the chat: what each request to a chat model cost, added up per model (no Streamlit code).

Taken from the Sprint 1 project (scanya-AE.AFA.updated0209.1.6, pricing.py): the price list
from the OpenRouter models endpoint and format_usd() are unchanged. Changed for this project:
the chat is a LangChain agent that makes several model requests per answer, and LangChain
returns the token counts of each request, so costs are added up per model in a "usage" dict
instead of per button click.

Cost of one request (request_cost()):
1. the cost OpenRouter reports with the answer, if there is one (exact);
2. otherwise input tokens x input price + output tokens x output price of that model, with
   prices from https://openrouter.ai/api/v1/models (an estimate).

A usage dict maps a model id to its totals, and is plain data so it can be saved as JSON:
    {"openai/gpt-6-luna": {"requests": 3, "input_tokens": 5200, "output_tokens": 640,
                           "cost": 0.0041, "unpriced": 0}}
"unpriced" counts requests whose cost is unknown (no reported cost and no price found).

Embedding requests are counted the same way, under the name of the embedding model: the
query of every search in a chat (reported by agent.py) and the documents added to the
knowledge base (page_library.py, build_index.py). The embedding model is not in the price
list of the chat models, so its price is a constant in settings.py.

estimate_answer_cost() is a different thing: not what was spent, but what one typical answer
would cost with a given model, to compare the models before choosing one.

Public: add_request(), request_cost(), estimate_answer_cost(), total_cost(), total_tokens(),
format_usd().
"""

from functools import lru_cache

import httpx

from scanya_ae_afa_updated0209_2_5 import settings

MODELS_ENDPOINT = "https://openrouter.ai/api/v1/models"


@lru_cache(maxsize=1)
def _all_model_prices() -> dict[str, tuple[float, float]]:
    """Model id -> (price per input token, price per output token) in USD. Fetched once per app run."""
    response = httpx.get(MODELS_ENDPOINT, timeout=15)
    response.raise_for_status()
    return {
        model["id"]: (float(model["pricing"]["prompt"]), float(model["pricing"]["completion"]))
        for model in response.json()["data"]
    }


def request_cost(model: str, input_tokens: int, output_tokens: int, reported_cost: float | None = None) -> float | None:
    """Cost in USD of one request to `model`.

    Returns `reported_cost` (from OpenRouter) if given, else tokens x the model's prices, or
    None if the prices cannot be fetched or the model is not in the price list.
    """
    if reported_cost is not None:
        return float(reported_cost)
    if model == settings.EMBEDDING_MODEL:
        return input_tokens * settings.EMBEDDING_PRICE_PER_MILLION_TOKENS / 1_000_000
    try:
        input_price, output_price = _all_model_prices()[model]
    except (httpx.HTTPError, KeyError):
        return None
    return input_tokens * input_price + output_tokens * output_price


def estimate_answer_cost(model: str) -> float | None:
    """Estimated cost in USD of one typical answer with `model` (None if its price is unknown).

    Typical = the token counts in settings.py; the price comes from the OpenRouter price list.
    """
    return request_cost(model, settings.TYPICAL_ANSWER_INPUT_TOKENS, settings.TYPICAL_ANSWER_OUTPUT_TOKENS)


def add_request(
    usage: dict, model: str, input_tokens: int, output_tokens: int, reported_cost: float | None = None
) -> None:
    """Add one request to the totals of `model` in the usage dict (changed in place)."""
    totals = usage.setdefault(
        model, {"requests": 0, "input_tokens": 0, "output_tokens": 0, "cost": 0.0, "unpriced": 0}
    )
    cost = request_cost(model, input_tokens, output_tokens, reported_cost)
    totals["requests"] += 1
    totals["input_tokens"] += input_tokens
    totals["output_tokens"] += output_tokens
    if cost is None:
        totals["unpriced"] += 1
    else:
        totals["cost"] += cost


def total_cost(usage: dict) -> float:
    """Cost in USD of all requests in a usage dict, over all models."""
    return sum(totals["cost"] for totals in usage.values())


def total_tokens(usage: dict) -> int:
    """Input + output tokens of all requests in a usage dict, over all models."""
    return sum(totals["input_tokens"] + totals["output_tokens"] for totals in usage.values())


def format_usd(amount: float, markdown: bool = True) -> str:
    """Format a (usually tiny) USD amount, e.g. $0.00038.

    For Streamlit Markdown the dollar sign is escaped (\\$): text between two $ signs is
    rendered as a math formula, which swallowed the signs and broke the bold text.
    `markdown=False` gives a plain "$", for the command line.
    """
    if amount >= 0.01:
        number = f"{amount:.3f}"
    elif amount >= 0.00001 or amount == 0:
        number = f"{amount:.5f}"
    else:  # E.g. the embedding of one search query: show its first two digits that are not zero.
        number = f"{float(f'{amount:.2g}'):.12f}".rstrip("0")
    return ("\\$" if markdown else "$") + number
