"""Shared setup for Lab 3: one chat client for all agents + the path to the Lab 2 MCP server.

Microsoft Agent Framework 1.19. We use the Chat Completions client because every endpoint of the day speaks it
(Foundry, the gateway, Ollama, LM Studio, the offline mock). OpenAIChatClient would use the Responses API instead.
"""
import os
import sys
from pathlib import Path

from agent_framework import ChatContext, MCPStdioTool, Message, chat_middleware
from agent_framework.openai import OpenAIChatCompletionClient
from dotenv import find_dotenv, load_dotenv
from pathlib import Path as _Path

_here = _Path(globals().get("__file__", ".")).resolve()   # no __file__ in a notebook: start at the cwd
for _folder in [*_here.parents, _Path.cwd(), *_Path.cwd().parents]:
    if (_folder / ".env").is_file():   # every .env from this file upward: the nearest one wins,
        load_dotenv(_folder / ".env")  # so labs/.env or one .env at the repo root both work
KEY = os.environ["GENAI_API_KEY"]
HEADERS = {"api-key": KEY} if os.getenv("GENAI_KEY_HEADER", "api-key") == "api-key" else None
# forwarded to the model with every request (low for gpt-5 models, none for local thinking models)
OPTIONS = {"reasoning_effort": os.environ["GENAI_REASONING_EFFORT"]} if os.getenv("GENAI_REASONING_EFFORT") else {}

LABS = next(p for p in Path(__file__).resolve().parents if (p / "_tools" / "make_starters.py").exists())  # labs/ root
LAB2_SERVER = LABS / "02-rag-mcp" / "python" / "solution" / "04_mcp_server.py"   # always the finished Lab 2 server
LAB2_INDEX = LABS / "02-rag-mcp" / "build" / "index.json"


def chat_client(model: str | None = None) -> OpenAIChatCompletionClient:
    return OpenAIChatCompletionClient(model=model or os.environ["GENAI_MODEL"], api_key=KEY,
                                      base_url=os.environ["GENAI_BASE_URL"], default_headers=HEADERS)


def kestrel_docs_tool() -> MCPStdioTool:
    """The Lab 2 MCP server as an agent tool (started as a child process over stdio)."""
    if not LAB2_INDEX.exists():
        sys.exit("The Lab 2 index is missing - run labs/02-rag-mcp/python/solution/01_ingest.py and 02_embed.py first.")
    return MCPStdioTool(name="kestrel_docs", command=sys.executable, args=[str(LAB2_SERVER)],
                        env=dict(os.environ),      # stdio children get a minimal environment otherwise
                        load_prompts=False)        # only the tools, not the server's prompt templates


def handoffs_as_user(me: str):
    """Chat middleware for agents that work on someone else's output (writer, critic).

    Workflows share one transcript: the researcher's notes reach the writer as an *assistant* message (with
    author_name="researcher"). Frontier models cope; small local models often think they have already answered and
    return an empty reply (verified with qwen3.5:2b on Ollama). Re-labelling other agents' turns as user turns fixes it.
    """
    @chat_middleware
    async def relabel(context: ChatContext, call_next):
        context.messages[:] = [
            Message("user", [f"[{m.author_name}] {m.text}"])
            if m.role == "assistant" and m.author_name and m.author_name != me and m.text else m
            for m in context.messages]
        await call_next()
    return relabel
