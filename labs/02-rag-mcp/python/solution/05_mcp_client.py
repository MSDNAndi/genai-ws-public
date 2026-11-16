"""Lab 2 · step 5 — talk to your MCP server from code (this is what every MCP host does under the hood).

The client starts 04_mcp_server.py as a child process, does the MCP handshake, then lists tools, calls
search_docs, reads a resource and lists prompts. Notice: the client never imports the server's code — it only
sends JSON messages over stdin/stdout, so the server could be written in any language.
"""
import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = Path(__file__).resolve().parent / "04_mcp_server.py"


async def main() -> None:
    # Gotcha: stdio MCP clients start the server with a MINIMAL environment (HOME, PATH, SHELL, TERM) — pass yours on,
    # or make sure the server can find labs/.env on its own (ours can). MCP hosts have an "env" field for this.
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)], env=dict(os.environ))
    # start the server process, connect to its stdin/stdout, and open an MCP session over them
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()                                     # handshake: versions + capabilities
        tools = await session.list_tools()                             # what a host shows the model
        print("tools:", [(t.name, t.description.split(".")[0]) for t in tools.tools])
        result = await session.call_tool("search_docs", {"query": "night flight altitude limit", "k": 2})
        for block in result.content:                                   # one text block (JSON) per hit
            print("hit:", json.dumps(json.loads(block.text), ensure_ascii=False)[:220])
        doc = await session.read_resource("kestrel://docs/kestrel_customer_service_policy")
        print("resource:", doc.contents[0].text[:120].replace("\n", " "), "...")
        prompts = await session.list_prompts()
        print("prompts:", [p.name for p in prompts.prompts])
    # leaving the "async with" closes the session and stops the server


asyncio.run(main())
