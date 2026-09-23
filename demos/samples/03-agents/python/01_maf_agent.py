# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "genaiclass",
#     "agent-framework-core==1.19.0",
#     "agent-framework-openai==1.14.4",
# ]
#
# [tool.uv.sources]
# genaiclass = { path = "../../../shared/python", editable = true }
# ///
# %% [markdown]
# # 01 - One agent (Microsoft Agent Framework)
#
# | | |
# |---|---|
# | **Pattern** | single agent: instructions + tools + memory |
# | **Communication** | request/response; conversation state held in a *session* |
# | **Use when** | one job, one persona. Start here and only add agents when this breaks |
# | **Watch out** | a session is memory you pay for - every turn resends the whole history |
#
# `Agent` is sample `01-foundations/04_tool_calling` - the hand-written loop -
# packaged up. Same model call, same tool dispatch, same `max_turns` guard; you
# just stop writing them.
#
# ```bash
# uv run 01_maf_agent.py --profile mock
# ```

# %%
import asyncio
from typing import Annotated

from agent_framework import Agent, tool
from pydantic import Field

from genaiclass import banner, get_profile, maf_client

profile = get_profile()
print(banner(profile))

# `maf_client` = OpenAIChatCompletionClient(model=..., base_url=..., api_key=...).
# That line is the ONLY provider-specific code in every MAF sample.
client = maf_client(profile)


# %% [markdown]
# ## Tools are plain functions
#
# `@tool` reads the signature, the type hints and the `Field` descriptions and
# builds the JSON schema you wrote by hand in Segment 1.

# %%
@tool
def get_route(
    origin: Annotated[str, Field(description="Start, e.g. Bellevue, WA")],
    destination: Annotated[str, Field(description="End, e.g. Redmond, WA")],
) -> dict:
    """How far it is and how long it takes to drive between two places."""
    return {"origin": origin, "destination": destination, "distance_km": 42.0, "duration_min": 35}


@tool
def get_current_weather(location: Annotated[str, Field(description="City and region")]) -> dict:
    """Current weather conditions for one place."""
    return {"location": location, "temperature_c": 18, "conditions": "light rain"}


agent = Agent(
    client,
    "You are a travel assistant. Use the tools; never guess numbers. Be brief.",
    name="travel",
    tools=[get_route, get_current_weather],
)


# %% [markdown]
# ## 1. One call - the loop runs inside
#
# `response.messages` shows what happened: assistant turn with tool calls, the
# tool results, then the final answer. That is the loop, recorded.

# %%
async def one_call() -> None:
    response = await agent.run("How far is Bellevue to Redmond, and what is the weather there?")
    for message in response.messages:
        print(f"  {message.role:<9} {(message.text or '[tool call]')[:90]}")
    print(f"\nanswer: {response.text}")


# %% [markdown]
# ## 2. Memory is a session, and you choose to keep one
#
# Without a session every `run` starts from nothing. With one, the framework
# replays the history for you. That replay is the cost: turn 20 sends turns 1-19
# again. Long-running agents need compaction or summarisation - MAF ships
# `compaction_strategy` for exactly that.

# %%
async def with_memory() -> None:
    session = agent.create_session()
    await agent.run("My name is Ada and I live in Redmond.", session=session)
    remembered = await agent.run("Where do I live?", session=session)
    forgotten = await agent.run("Where do I live?")  # no session -> no memory
    print(f"with session   : {remembered.text}")
    print(f"without session: {forgotten.text}")


# %% [markdown]
# ## 3. Streaming
#
# Same call, `stream=True`: token-sized updates as they are produced. This is
# what makes a UI feel alive, and what the hosted-agent samples (12, 13) turn
# into a server-sent event stream.

# %%
async def streaming() -> None:
    async for update in agent.run("Say hello in five words.", stream=True):
        print(update.text or "", end="", flush=True)
    print()


# %% [markdown]
# ## Run it
#
# One `asyncio.run` for the whole script, not one per section: the async HTTP
# client inside the agent is bound to the event loop that first used it, and a
# second `asyncio.run` hands it a closed one ("Event loop is closed").

# %%
async def main() -> None:
    print("--- 1. one call")
    await one_call()
    print("\n--- 2. memory")
    await with_memory()
    print("\n--- 3. streaming")
    await streaming()


asyncio.run(main())
