"""Lab 3 · step 4 — add a critic: researcher -> writer -> critic -> writer (revise), as a group chat with a fixed
speaking order and a hard round limit. The critic can end it early by saying APPROVED."""
import asyncio

from agent_framework import Agent
from agent_framework.orchestrations import GroupChatBuilder

from lab3_common import OPTIONS, chat_client, handoffs_as_user, kestrel_docs_tool

TASK = "Write the FAQ entry: 'Can I send a 150 Wh power bank with Kestrel, and what happens if my parcel is lost?'"


def next_speaker(state) -> str:
    # >>> TODO 2: return who speaks next - round 0 the researcher, then writer and critic take turns
    if state.current_round == 0:
        return "researcher"
    return "writer" if state.current_round % 2 else "critic"
    # <<< TODO


def critic_approved(conversation) -> bool:
    return any("APPROVED" in (m.text or "") for m in conversation if m.author_name == "critic")


async def main() -> None:
    client = chat_client()
    async with kestrel_docs_tool() as docs:
        researcher = Agent(client=client, name="researcher", tools=[docs], default_options=OPTIONS,
                           instructions="Collect the facts with search_docs. Bullet list with chunk ids.")
        writer = Agent(client=client, name="writer", default_options=OPTIONS, middleware=[handoffs_as_user("writer")],
                       instructions="Write or revise the FAQ entry (max 90 words) from the researcher's facts and "
                                    "the critic's feedback.")
        critic = Agent(client=client, name="critic", default_options=OPTIONS, middleware=[handoffs_as_user("critic")],
                       instructions="Check the latest FAQ draft against the researcher's facts. If it is correct, "
                                    "complete and under 90 words, reply only APPROVED. Otherwise list the fixes.")
        workflow = GroupChatBuilder(participants=[researcher, writer, critic], selection_func=next_speaker,
                                    max_rounds=5, termination_condition=critic_approved, output_from=[writer]).build()
        result = await workflow.run(TASK)
        # outputs = every writer turn (output_from=[writer]) + the orchestrator's closing status line
        drafts = [o for o in result.get_outputs() if o.messages and o.messages[-1].author_name == "writer"]
        for n, draft in enumerate(drafts, 1):
            print(f"--- draft {n}:\n{draft.text.strip()}\n")
        print("Critic approved." if critic_approved([m for o in result.get_outputs() for m in o.messages])
              else "Stopped by the round limit.")


asyncio.run(main())
