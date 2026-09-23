# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "genaiclass",
#     "openai==3.18.0",
#     "python-dotenv==1.2.3",
#     "numpy>=1.26",
#     "pydantic>=2.10,<3",
#     "mcp==1.30.0",
#     "markitdown[pdf]==0.1.8",
#     "pillow>=10",
# ]
#
# [tool.uv.sources]
# genaiclass = { path = "../../../shared/python", editable = true }
# ///
import sys
# Windows consoles default to cp1252; one non-ASCII print (a check mark, an arrow)
# kills a demo mid-run. Switch this process's console streams to UTF-8.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, OSError):
        pass
# These samples came from the labs and read GENAI_* variables directly. --profile <name>
# (the runner always passes one) maps a providers.json profile onto those variables, so
# `--profile mock` or `p` in the runner work here exactly like in Segments 1 and 3.
if "--profile" in sys.argv:
    import os
    from genaiclass import get_profile
    _i = sys.argv.index("--profile"); _name = sys.argv[_i + 1]; del sys.argv[_i:_i + 2]
    _p = get_profile(_name)
    os.environ.update(GENAI_BASE_URL=_p.base_url, GENAI_API_KEY=_p.api_key or "none",
                      GENAI_MODEL=_p.model, GENAI_EMBED_MODEL=_p.embed_model,
                      GENAI_KEY_HEADER="api-key" if _p.key_header == "api-key" else "authorization")
    if _name == "mock":                      # the mock has no reasoning knob
        os.environ.pop("GENAI_REASONING_EFFORT", None)
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


# >>> TODO 3: register a tool `search_docs(query, k=4)` that returns the top-k chunks (id, doc, score, text) — the docstring becomes the tool description the model sees
@mcp.tool()
def search_docs(query: str, k: int = 4) -> list[dict]:
    """Search the Kestrel Drone Logistics documents (operations handbook, customer service policy, Q3 incident
    review). Returns the k most relevant text chunks with their document name, chunk id and similarity score."""
    return [{"id": h["id"], "doc": h["doc"], "score": h["score"], "text": h["text"]} for h in index.search(query, k)]
# <<< TODO


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
