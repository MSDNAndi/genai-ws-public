# STARTER - complete the TODO block(s). The finished version is in solution/04_mcp_server.py
"""Lab 2 · step 4 — expose the retrieval as an MCP server (stdio). Any MCP host can now use your documents:
Claude Code, GitHub Copilot (VS Code / CLI), LM Studio, MCP Inspector ... and the agents in Lab 3.

Never print() in a stdio MCP server — stdout carries the protocol. Log to stderr.
Runs on mcp 1.30 (pinned for the labs) and on mcp 2.x (FastMCP was renamed MCPServer).
"""
import logging
import sys
from pathlib import Path

try:
    from mcp.server.mcpserver import MCPServer                  # mcp >= 2.0
except ImportError:
    from mcp.server.fastmcp import FastMCP as MCPServer         # mcp 1.x

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kestrel_search import BUILD, LAB2, Index                   # noqa: E402

logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
mcp = MCPServer("kestrel-docs")
index = Index()


# TODO 3: register a tool `search_docs(query, k=4)` that returns the top-k chunks (id, doc, score, text) — the docstring becomes the tool description the model sees
raise NotImplementedError("TODO 3: register a tool `search_docs(query, k=4)` that returns the top-k chunks (id, doc, score, text) — the docstring becomes the tool description the model sees")


@mcp.resource("kestrel://docs/{name}")
def get_document(name: str) -> str:
    """The full extracted text of one document, e.g. kestrel://docs/kestrel_operations_handbook"""
    path = BUILD / f"{Path(name).stem}.md"
    return (path if path.exists() else LAB2 / "data" / "prebuilt" / path.name).read_text(encoding="utf-8")


@mcp.prompt()
def cite_answer(question: str) -> str:
    """A reusable prompt: answer a question with citations from search_docs."""
    return f"Use the search_docs tool, then answer with [doc#chunk] citations. Question: {question}"


if __name__ == "__main__":
    mcp.run()                                                   # stdio transport
