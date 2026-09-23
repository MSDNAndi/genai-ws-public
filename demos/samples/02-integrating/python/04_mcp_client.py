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
# %% [markdown]
# # 04 - MCP client talking to our own MCP server
#
# talk to your MCP server from code (this is what every MCP host does under the hood).
#
#
# *Ported from the course labs (`labs/02-rag-mcp/python/solution`) on 2026-09-23.*
# %%
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
import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = Path(__file__).resolve().parent / "mcp_server.py"


async def main() -> None:
    # Gotcha: stdio MCP clients start the server with a MINIMAL environment (HOME, PATH, SHELL, TERM) — pass yours on,
    # or make sure the server can find labs/.env on its own (ours can). MCP hosts have an "env" field for this.
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)], env=dict(os.environ))
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        tools = await session.list_tools()
        print("tools:", [(t.name, t.description.split(".")[0]) for t in tools.tools])
        result = await session.call_tool("search_docs", {"query": "night flight altitude limit", "k": 2})
        for block in result.content:
            print("hit:", json.dumps(json.loads(block.text), ensure_ascii=False)[:220])
        doc = await session.read_resource("kestrel://docs/kestrel_customer_service_policy")
        print("resource:", doc.contents[0].text[:120].replace("\n", " "), "...")
        prompts = await session.list_prompts()
        print("prompts:", [p.name for p in prompts.prompts])


asyncio.run(main())
