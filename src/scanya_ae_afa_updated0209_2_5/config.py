"""API client setup: one OpenAI SDK client, pointed at OpenRouter.

Taken from the Sprint 1 project (scanya-AE.AFA.updated0209.1.6, config.py): PROVIDERS and
get_client(), without the "OpenAI" provider, which this project does not use. Added for this project: get_chat_model(), because the LangChain
agent needs a LangChain chat model instead of the plain SDK client.

API keys are read from the environment. The .env file in the project root (git-ignored; see
.env.example) is loaded first, without overriding variables that are already set, so a key
stored as a Windows environment variable works as well.

On Streamlit Community Cloud there is no .env: the key goes into the app's Secrets
(see .streamlit/secrets.toml.example). Streamlit passes top-level secrets on as environment
variables, so this module finds the key the same way and needs no Streamlit code.

Public functions: get_client(), get_chat_model().
"""

import os

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from openai import OpenAI

# Provider name -> (API base URL, environment variable holding its API key).
PROVIDERS = {
    "OpenRouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
}


def get_client(provider: str) -> OpenAI:
    """Return an OpenAI SDK client for `provider` (only "OpenRouter").

    OpenRouter speaks the same API as OpenAI, so the OpenAI SDK works with its base URL and
    key. Used here for the embeddings (embeddings.py).

    Raises:
        ValueError: for an unknown provider.
        KeyError: if the provider's API key is missing from .env / the environment.
    """
    if provider not in PROVIDERS:
        raise ValueError(f"Unsupported API provider: {provider}")
    load_dotenv()  # Read .env into the environment (does not override variables already set).
    base_url, key_variable = PROVIDERS[provider]
    return OpenAI(base_url=base_url, api_key=os.environ[key_variable])


def get_chat_model(model_name: str, temperature: float = 0.0) -> BaseChatModel:
    """Return a LangChain chat model for an OpenRouter model id (e.g. "openai/gpt-6-luna").

    Uses the same key as get_client("OpenRouter"). `temperature` 0 makes the answers as
    repeatable as the model allows; the app passes settings.TEMPERATURE.

    Raises:
        KeyError: if OPENROUTER_API_KEY is missing from .env / the environment.
    """
    load_dotenv()
    _, key_variable = PROVIDERS["OpenRouter"]
    return init_chat_model(
        model_name, model_provider="openrouter", api_key=os.environ[key_variable], temperature=temperature
    )
