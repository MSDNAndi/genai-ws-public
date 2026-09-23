"""Lab 3 · step 2 — give the agent the Lab 2 documents through MCP. No adapter code: an MCP server IS a tool source."""
import asyncio

from agent_framework import Agent

from lab3_common import OPTIONS, chat_client, kestrel_docs_tool


async def main() -> None:
    async with kestrel_docs_tool() as docs:               # starts 04_mcp_server.py, lists its tools
        agent = Agent(client=chat_client(), name="KestrelSupport", tools=[docs], default_options=OPTIONS,
                      instructions="You answer questions about Kestrel Drone Logistics. Always call search_docs "
                                   "first and cite the chunk ids you used, like (kestrel_operations_handbook#2). "
                                   "If the documents do not answer the question, say so.")
        for question in ["Can I fly a K-2 Sparrow at night at 100 m?",
                         "My payload was lost in August. How quickly will someone call me, and what do I get?"]:
            response = await agent.run(question)
            print(f"> {question}\n  {response.text.strip()}\n")


asyncio.run(main())
