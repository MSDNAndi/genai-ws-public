"""Shared setup for Lab 3 - read it once, then every step file stays short.

Three helpers the step files import:
  chat_client()        -> the connection to the model (one per model name)
  kestrel_docs_tool()  -> the Lab 2 MCP server, packaged as a tool an agent can call
  handoffs_as_user()   -> a small fix so the *next* agent in a workflow really answers (see below)

Microsoft Agent Framework (MAF) 1.19. We use the Chat Completions client because every endpoint of the day speaks it
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
# Sent with every request: GENAI_REASONING_EFFORT from labs/.env ("low" for gpt-5 models). The workshop gateway
# drops it for models that do not support it, so switching models only needs GENAI_MODEL.
OPTIONS = {"reasoning_effort": os.environ["GENAI_REASONING_EFFORT"]} if os.getenv("GENAI_REASONING_EFFORT") else {}

LABS = next(p for p in Path(__file__).resolve().parents if (p / "_tools" / "make_starters.py").exists())  # labs/ root
LAB2_SERVER = LABS / "02-rag-mcp" / "python" / "solution" / "04_mcp_server.py"   # always the finished Lab 2 server
LAB2_INDEX = LABS / "02-rag-mcp" / "build" / "index.json"


def chat_client(model: str | None = None) -> OpenAIChatCompletionClient:
    """The model connection an Agent talks to. Default model: GENAI_MODEL (08_team passes one per agent)."""
    return OpenAIChatCompletionClient(model=model or os.environ["GENAI_MODEL"], api_key=KEY,
                                      base_url=os.environ["GENAI_BASE_URL"], default_headers=HEADERS)


def kestrel_docs_tool() -> MCPStdioTool:
    """The Lab 2 MCP server as an agent tool (started as a child process over stdio).

    MCPStdioTool = "start this program, use its tools". Use it with `async with`: entering starts the server and
    lists its tools (search_docs), leaving stops it again.
    """
    if not LAB2_INDEX.exists():
        sys.exit("The Lab 2 index is missing - run labs/02-rag-mcp/python/solution/01_ingest.py and 02_embed.py first.")
    return MCPStdioTool(name="kestrel_docs", command=sys.executable, args=[str(LAB2_SERVER)],
                        env=dict(os.environ),      # stdio children get a minimal environment otherwise
                        load_prompts=False)        # only the tools, not the server's prompt templates


def handoffs_as_user(me: str):
    """Chat middleware for agents that work on someone else's output (writer, critic).

    Why it exists: in a workflow all agents share one transcript. The researcher's notes reach the writer as an
    *assistant* message - to the model that reads like "I already said this". Frontier models cope; small local models
    often believe they have already answered and return an EMPTY reply (verified with qwen3.5:2b on Ollama).
    The fix: just before each model call, turn other agents' turns into user turns: "[researcher] <the notes>".
    Middleware = a function that runs around every model call. `me` = this agent's name (its own turns stay as they are).
    """
    @chat_middleware                                       # runs before every model call of this agent
    async def relabel(context: ChatContext, call_next):
        context.messages[:] = [                            # rewrite the message list in place
            Message("user", [f"[{m.author_name}] {m.text}"])
            if m.role == "assistant" and m.author_name and m.author_name != me and m.text else m
            for m in context.messages]
        await call_next()                                  # now send the (rewritten) messages to the model
    return relabel
