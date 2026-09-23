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
# # 03 - Concurrent fan-out / fan-in
#
# | | |
# |---|---|
# | **Pattern** | concurrent: the same input goes to N agents at once, results are aggregated |
# | **Communication** | **broadcast** in, **aggregate** out - the agents never see each other |
# | **Use when** | independent perspectives: review panels, multi-source research, voting, ensembles |
# | **Watch out** | N agents = N times the cost; the aggregator is where quality is decided |
#
# ```bash
# uv run 03_maf_concurrent.py --profile mock
# ```

# %%
import asyncio

from agent_framework import Agent
from agent_framework.orchestrations import ConcurrentBuilder

from genaiclass import banner, get_profile, maf_client

profile = get_profile()
client = maf_client(profile)
print(banner(profile))

# %% [markdown]
# ## A review panel
#
# Isolation is the feature. The skeptic cannot be talked round by the optimist,
# because neither ever sees the other's answer - unlike a group chat (sample 05).

# %%
panel = [
    Agent(client, "You are an optimist. Give the strongest case FOR the idea in two sentences.",
          name="optimist"),
    Agent(client, "You are a skeptic. Give the strongest case AGAINST the idea in two sentences.",
          name="skeptic"),
    Agent(client, "You are a finance lead. Estimate cost and payback in two sentences.",
          name="finance"),
]
IDEA = "Replace our support hotline with an AI agent next quarter."


# %% [markdown]
# ## 1. Default aggregation
#
# Out of the box the results are merged into one response, one message per
# agent. Nothing is summarised - you get the raw panel.

# %%
async def default_aggregation() -> None:
    result = await ConcurrentBuilder(participants=panel).build().run(IDEA)
    for message in result.get_outputs()[-1].messages:
        print(f"  {message.author_name:<9} {message.text[:100]}")


# %% [markdown]
# ## 2. Your own aggregator
#
# The fan-in step is ordinary code. Here: a judge agent reads all three and
# decides. It could just as well be a vote count, a max-score pick, or a merge -
# this is the "reduce" of map/reduce, and it deserves as much design as the agents.

# %%
judge = Agent(client, "You are the decision maker. Weigh the panel and give a go/no-go in one line.",
              name="judge")


async def judged(results) -> str:
    panel_text = "\n".join(f"{r.executor_id}: {r.agent_response.text}" for r in results)
    verdict = await judge.run(f"Idea: {IDEA}\n\nPanel:\n{panel_text}")
    return verdict.text


async def custom_aggregation() -> None:
    workflow = ConcurrentBuilder(participants=panel).with_aggregator(judged).build()
    result = await workflow.run(IDEA)
    print(f"  verdict: {result.get_outputs()[-1]}")


async def main() -> None:
    print("--- 1. default aggregation (the raw panel)")
    await default_aggregation()
    print("\n--- 2. custom aggregator (a judge decides)")
    await custom_aggregation()


asyncio.run(main())
