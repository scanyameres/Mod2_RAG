"""Settings of the app in one place: folders, model names, chunking, search and agent
parameters, limits. Only constants, no logic. (API keys and clients are in config.py.)

When does a change take effect?
- Chunking and embedding settings: only after "Rebuild index" on the Knowledge base page,
  because they decide what is stored in the index.
- Everything else: at the next start of the app.
"""

from pathlib import Path

# --- Folders (resolved from this file, so they work from any working directory) ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CATEGORIES_FILE = PROJECT_ROOT / "categories.toml"
DATA_DIR = PROJECT_ROOT / "data"
LIBRARY_DIR = DATA_DIR / "library"  # Knowledge-base files, one sub-folder per category.
INDEX_DIR = DATA_DIR / "index"  # LanceDB database (built from the library, can be rebuilt).
USERS_DIR = DATA_DIR / "users"  # History of logged-in users, one JSON file each (user_store.py).
AUTH_CONFIG_FILE = PROJECT_ROOT / "config.yaml"  # User accounts and login cookie (auth.py).

# --- Models (OpenRouter ids) ---
# Chat models the user can choose from. The first one is the default.
CHAT_MODELS = (
    "openai/gpt-6-luna",
    "anthropic/claude-sonnet-5.5",
    "openai/gpt-6.1-sol",
)
# 0 = the model picks the most likely wording every time, so the same question gives (nearly)
# the same answer. Wanted here: the assistant quotes rules and values, it should not vary them.
TEMPERATURE = 0.0
# Multilingual, 1536 numbers per text. Changing it requires rebuilding the index
# (Knowledge base page), because vectors of different models cannot be compared.
EMBEDDING_MODEL = "openai/text-embedding-3-small"
EMBEDDING_BATCH_SIZE = 100  # Texts per embedding request.
# USD per million tokens of EMBEDDING_MODEL on OpenRouter (checked 2026-11-24; update it with
# the model). Used for the estimate shown before documents are embedded, and for the cost of
# an embedding request when OpenRouter does not report it.
EMBEDDING_PRICE_PER_MILLION_TOKENS = 0.02

# --- Chunking (characters) ---
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150

# --- Search ---
TOP_K = 6  # Passages handed to the chat model per search (default of the slider in Settings).
TOP_K_MAX = 12  # Upper end of that slider. More passages = more tokens per request.
CANDIDATES_PER_SEARCH = 20  # Passages fetched by each of the two searches before merging.
RRF_CONSTANT = 60  # Usual constant of Reciprocal Rank Fusion (see retrieval.py).

# --- Agent ---
# Earlier messages sent along with a new question (older ones are dropped to limit tokens).
MAX_HISTORY_MESSAGES = 12
# Upper limit of steps per answer, so a confused model cannot loop forever. A search takes two
# steps (the model asks, the tool answers) and the final answer one: 16 allows about 7 searches.
MAX_AGENT_STEPS = 16

# --- Cost estimate per model (shown under the Model select box) ---
# Tokens of one typical answer, over all its requests to the chat model. A rough figure for
# comparing models: an answer needs 2-3 requests, each sends the system prompt and the history
# (about 1,300 tokens), and each search adds about 1,500 tokens of passages. Measured so far
# only with an empty knowledge base (about 2,400 input / 220 output tokens per answer).
TYPICAL_ANSWER_INPUT_TOKENS = 6_000
TYPICAL_ANSWER_OUTPUT_TOKENS = 300

# --- Limits (input validation) ---
MAX_QUESTION_LENGTH = 2_000  # Characters per chat message.
MAX_UPLOAD_MB = 25  # Per uploaded file (knowledge base and project input).
ALLOWED_EXTENSIONS = (".pdf", ".txt", ".md")
# Project input (the user's own files and notes) is sent to the chat model with every
# question, so its total length is capped. About 4 characters make one token.
MAX_PROJECT_INPUT_CHARS = 30_000
MAX_DOCUMENT_CHARS = 30_000  # Longest work product the assistant may write.
