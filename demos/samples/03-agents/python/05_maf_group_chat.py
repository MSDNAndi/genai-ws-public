# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "genaiclass",
#     "agent-framework-core==1.19.0",
#     "agent-framework-openai==1.14.4",
#     "agent-framework-orchestrations==1.2.0",
# ]
#
# [tool.uv.sources]
# genaiclass = { path = "../../../shared/python", editable = true }
# ///
# %% [markdown]
# # 05 - Group chat (shared transcript)
#
# | | |
# |---|---|
# | **Pattern** | group chat: several agents take turns in one conversation, a manager picks who speaks |
# | **Communication** | **shared blackboard** - everyone reads the whole transcript and writes to it |
# | **Use when** | iterative refinement between roles: writer + critic, planner + reviewer, debate |
# | **Watch out** | it can loop forever politely agreeing; always set `max_rounds`, and prefer a deterministic manager until you need an LLM one |
#
# Contrast with sample 03 (concurrent): there the agents were isolated on
# purpose. Here they are meant to influence each other.
#
# ```bash
# uv run 05_maf_group_chat.py --profile mock
# ```

# %%
import asyncio

from agent_framework import Agent
from agent_framework.orchestrations import GroupChatBuilder, GroupChatState

from genaiclass import banner, get_profile, maf_client

profile = get_profile()
client = maf_client(profile)
print(banner(profile))


def build_participants() -> list[Agent]:
    return [
        Agent(client, "You are a writer. Draft or revise a tagline for the product in the chat.",
              name="writer", description="Drafts and revises taglines"),
        Agent(client, "You are a critic. Name the single biggest weakness of the latest tagline.",
              name="critic", description="Critiques the latest tagline"),
    ]


# %% [markdown]
# ## The manager is just a function
#
# `selection_func` receives the `GroupChatState` - round number, participants,
# the whole conversation - and returns the name of the next speaker. Round-robin
# is two lines, costs nothing and is perfectly predictable.
#
# The alternative is `orchestrator_agent=<an Agent>`: an LLM reads the
# transcript and picks. More flexible, one extra model call per turn, and a new
# way to go wrong. Start deterministic.

# %%
def round_robin(state: GroupChatState) -> str:
    names = list(state.participants)
    return names[state.current_round % len(names)]


def build_workflow():
    return GroupChatBuilder(
        participants=build_participants(),
        selection_func=round_robin,
        max_rounds=4,  # hard stop; the manager's own opening round counts too
        # By default only the manager's final message is a workflow output and
        # the participants' turns are hidden. Surface them as `intermediate` events:
        intermediate_output_from="all",
    ).build()


# %% [markdown]
# ## Watch the transcript grow
#
# The context counter in each (mock) reply goes up every turn: each agent is
# sent everything said so far. That is the blackboard - and the cost curve.

# %%
async def main() -> None:
    speaker = None
    async for event in build_workflow().run("Product: a solar-powered bike lock.", stream=True):
        text = getattr(event.data, "text", None)
        if event.type in ("intermediate", "output") and text:
            if event.executor_id != speaker:
                speaker = event.executor_id
                print(f"\n[{speaker}] ", end="")
            print(text, end="", flush=True)
    print()


asyncio.run(main())
