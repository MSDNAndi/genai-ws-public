"""Lab 3 · step 3 — two agents, one workflow: a researcher (with the MCP tool) hands its notes to a writer."""
import asyncio

from agent_framework import Agent
from agent_framework.orchestrations import SequentialBuilder

from lab3_common import OPTIONS, chat_client, handoffs_as_user, kestrel_docs_tool

TASK = "Customer question: 'My Standard delivery arrived 41 minutes late - what do I get, and why was it late?'"


async def main() -> None:
    client = chat_client()
    async with kestrel_docs_tool() as docs:
        # >>> TODO 1: create the researcher (uses the docs tool, returns cited facts only) and the writer (turns the facts into a friendly 80-word reply)
        researcher = Agent(client=client, name="researcher", tools=[docs], default_options=OPTIONS,
                           instructions="Find the facts needed to answer the customer. Call search_docs. Return a "
                                        "bullet list of facts, each with the chunk id it came from. No prose.")
        writer = Agent(client=client, name="writer", default_options=OPTIONS, middleware=[handoffs_as_user("writer")],
                       instructions="You write replies to Kestrel customers: friendly, at most 80 words, only facts "
                                    "from the researcher's notes, no chunk ids in the text.")
        # <<< TODO
        workflow = SequentialBuilder(participants=[researcher, writer], intermediate_output_from=[researcher]).build()
        result = await workflow.run(TASK)
        for item in result.get_intermediate_outputs():
            print("RESEARCHER NOTES:\n" + item.text[:800] + "\n")
        print("WRITER:\n" + (result.get_outputs()[-1].text or "(empty reply - see handoffs_as_user in lab3_common.py)"))


asyncio.run(main())
