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
# # 02 - Sequential pipeline
#
# | | |
# |---|---|
# | **Pattern** | sequential: A -> B -> C, fixed order, each step refines the last |
# | **Communication** | the **conversation is handed down the chain** - every agent sees everything before it |
# | **Use when** | the steps are known up front: draft -> review -> translate, extract -> validate -> format |
# | **Watch out** | context grows at every hop, and a bad early step poisons everything after it |
#
# ```bash
# uv run 02_maf_sequential.py --profile mock
# ```

# %%
import asyncio

from agent_framework import Agent
from agent_framework.orchestrations import SequentialBuilder

from genaiclass import banner, get_profile, maf_client

profile = get_profile()
client = maf_client(profile)
print(banner(profile))

# %% [markdown]
# ## Three specialists, one direction
#
# Narrow instructions per agent are the whole point. One agent told to "write,
# then critique, then fix" does all three worse than three agents doing one each.

# %%
def build_workflow():
    writer = Agent(client, "You are a copywriter. Write one punchy product slogan.", name="writer")
    editor = Agent(client, "You are an editor. Tighten the slogan above; return only the new slogan.",
                   name="editor")
    translator = Agent(client, "You are a translator. Translate the final slogan into German.",
                       name="translator")
    return SequentialBuilder(participants=[writer, editor, translator]).build()


# %% [markdown]
# ## A built workflow is a conversation, not a function
#
# Why `build_workflow()` instead of one module-level `workflow`: a built workflow
# **keeps state between runs**. Run the same instance twice and the second run
# carries the first run's messages (verified on 1.19: 3 -> 6 -> 8 messages in
# context over three runs). In a web service that is one user's conversation
# leaking into the next user's request. Build one per conversation.


# %% [markdown]
# ## Watch the hand-offs
#
# Streaming the workflow yields events, not just text. `executor_invoked` /
# `executor_completed` show *who* holds the conversation at each moment - this
# is the communication pattern made visible.

# %%
async def run_pipeline() -> None:
    async for event in build_workflow().run("A reusable water bottle that tracks hydration.", stream=True):
        if event.type == "executor_invoked" and event.executor_id in {"writer", "editor", "translator"}:
            print(f"\n-> {event.executor_id} receives the conversation")
        elif event.type == "output":
            print(getattr(event.data, "text", "") or "", end="", flush=True)
    print()


# %% [markdown]
# ## What the last agent actually saw
#
# The final output is the translator's response, but the translator was sent the
# user prompt *and* both earlier answers. Set
# `SequentialBuilder(..., chain_only_agent_responses=True)` to pass only the
# previous agent's answer instead - cheaper, and less room for the original
# prompt to override a later step.

# %%
async def final_only() -> None:
    result = await build_workflow().run("A reusable water bottle that tracks hydration.")
    final = result.get_outputs()[-1]
    print(f"final output ({final.messages[-1].author_name}): {final.text}")


async def main() -> None:
    print("--- streamed hand-offs")
    await run_pipeline()
    print("\n--- final output only")
    await final_only()


asyncio.run(main())
