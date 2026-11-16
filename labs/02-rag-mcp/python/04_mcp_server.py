# STARTER - complete the TODO block(s). The finished version is in solution/04_mcp_server.py
"""Lab 2 · step 4 — an MCP server is just functions with descriptions.

MCP (Model Context Protocol = plug-in standard for AI tools) lets any host — Claude Code, GitHub Copilot, LM Studio,
MCP Inspector, the agents in Lab 3 — use our search. We publish three things:
  tool     search_docs  (a function the model may call; its docstring is the description the model reads)
  resource kestrel://docs/<name>  (read-only data, here: a whole document)
  prompt   cite_answer  (a reusable prompt template)
Notice: never print() here — with stdio (talking over stdin/stdout) stdout IS the protocol. Log to stderr.
Runs on mcp 1.30 (pinned for the labs) and on mcp 2.x (FastMCP was renamed MCPServer).
"""
import logging
import sys
from pathlib import Path

try:
    from mcp.server.mcpserver import MCPServer                  # mcp >= 2.0
except ImportError:
    from mcp.server.fastmcp import FastMCP as MCPServer         # mcp 1.x

sys.path.insert(0, str(Path(__file__).resolve().parent))         # hosts start us from anywhere: find kestrel_search.py
from kestrel_search import BUILD, LAB2, Index                   # noqa: E402

logging.basicConfig(stream=sys.stderr, level=logging.WARNING)   # logs -> stderr, never stdout
mcp = MCPServer("kestrel-docs")                                 # the name hosts show for this server
index = Index()                                                 # the same search as step 3


# --- tool: the model decides when to call it, based on the name + docstring + typed arguments ----------------------
# TODO 3: register a tool `search_docs(query, k=4)` that returns the top-k chunks (id, doc, score, text) — the docstring becomes the tool description the model sees
raise NotImplementedError("TODO 3: register a tool `search_docs(query, k=4)` that returns the top-k chunks (id, doc, score, text) — the docstring becomes the tool description the model sees")


# --- resource: data the host can read by URI; {name} in the URI becomes the function argument ----------------------
@mcp.resource("kestrel://docs/{name}")
def get_document(name: str) -> str:
    """The full extracted text of one document, e.g. kestrel://docs/kestrel_operations_handbook"""
    path = BUILD / f"{Path(name).stem}.md"                      # keep only the stem: "../x.pdf" -> "x.md"
    return (path if path.exists() else LAB2 / "data" / "prebuilt" / path.name).read_text(encoding="utf-8")


# --- prompt: a ready-made instruction a user can pick in the host ---------------------------------------------------
@mcp.prompt()
def cite_answer(question: str) -> str:
    """A reusable prompt: answer a question with citations from search_docs."""
    return f"Use the search_docs tool, then answer with [doc#chunk] citations. Question: {question}"


if __name__ == "__main__":
    mcp.run()                                                   # stdio transport: wait for requests on stdin
