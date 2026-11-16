# STARTER - complete the TODO block(s). The finished version is in solution/03_workflow.py
"""Lab 3 · step 3 — two agents, one workflow: a researcher (with the MCP tool) hands its notes to a writer.

Workflow = fixed steps that YOU decide (researcher first, then writer) - no model picks the order. Each agent has one
small job. What to notice: the writer has no tool; it only sees the researcher's notes in the shared conversation.
"""
import asyncio

from agent_framework import Agent
from agent_framework.orchestrations import SequentialBuilder

from lab3_common import OPTIONS, chat_client, handoffs_as_user, kestrel_docs_tool

TASK = "Customer question: 'My Standard delivery arrived 41 minutes late - what do I get, and why was it late?'"


async def main() -> None:
    client = chat_client()                                 # one model connection, shared by both agents
    async with kestrel_docs_tool() as docs:
        # TODO 1: create the researcher (uses the docs tool, returns cited facts only) and the writer (turns the facts into a friendly 80-word reply)
        raise NotImplementedError("TODO 1: create the researcher (uses the docs tool, returns cited facts only) and the writer (turns the facts into a friendly 80-word reply)")
        # SequentialBuilder = run agents one after another; each sees the conversation so far and adds its turn.
        # intermediate_output_from=[researcher]: also give us the researcher's notes, not only the final reply.
        workflow = SequentialBuilder(participants=[researcher, writer], intermediate_output_from=[researcher]).build()
        result = await workflow.run(TASK)                  # TASK becomes the first (user) message
        for item in result.get_intermediate_outputs():
            print("RESEARCHER NOTES:\n" + item.text[:800] + "\n")
        print("WRITER:\n" + (result.get_outputs()[-1].text or "(empty reply - see handoffs_as_user in lab3_common.py)"))


asyncio.run(main())
