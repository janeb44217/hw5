"""Paths, model, and run limits for the Campus Customs agent team."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider

BACKEND = Path(__file__).resolve().parent
PROJECT = BACKEND.parent
PROMPTS = BACKEND / "prompts"
OUTPUT = PROJECT / "output"
AUDIT_TRAIL = OUTPUT / "audit_trail.json"

ORIGINAL_DB = PROJECT / "data" / "campus_customs.db"
WORKING_DB = PROJECT / "data" / "campus_customs_new.db"
MCP_SERVER = PROJECT / "mcp_server" / "server.py"

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

# PORTKEY_API_KEY lives in a .env in this project or the course folder above it.
for env_dir in (PROJECT, PROJECT.parent):
    load_dotenv(env_dir / ".env")

# The assignment allows exactly one model, for every agent. Not overridable.
MODEL_NAME = "gpt-6-luna"
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"

# --- token / loop guardrails -------------------------------------------------
MAX_DELEGATION_DEPTH = 2          # boss -> specialist -> specialist, no deeper
MAX_DELEGATIONS_PER_TICKET = 8    # total ask_agent calls in one ticket run
BOSS_REQUEST_LIMIT = 14           # model calls in the Boss loop for one ticket
SPECIALIST_REQUEST_LIMIT = 8      # model calls in a specialist loop per delegation
TOTAL_TOKENS_PER_AGENT_RUN = 80_000
AUDIT_TEXT_LIMIT = 2_000          # chars kept per field in the audit trail


def require_api_key() -> str:
    key = os.getenv("PORTKEY_API_KEY", "").strip()
    if not key:
        raise RuntimeError("PORTKEY_API_KEY is not set. Add it to a .env file.")
    return key


def build_model() -> OpenAIResponsesModel:
    # Portkey speaks the OpenAI API; the Responses endpoint supports tools for gpt-6-luna.
    client = AsyncOpenAI(api_key=require_api_key(), base_url=PORTKEY_BASE_URL)
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))


def mcp_command() -> tuple[str, list[str]]:
    """How to launch the MCP server: same interpreter, same server file as .mcp.json."""
    return sys.executable, [str(MCP_SERVER)]


def load_prompt(name: str) -> str:
    return (PROMPTS / name).read_text(encoding="utf-8")
