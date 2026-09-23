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
# # 06 - Agents as tools (supervisor / hierarchical)
#
# | | |
# |---|---|
# | **Pattern** | supervisor: one orchestrator agent delegates sub-tasks to specialist agents |
# | **Communication** | **encapsulated function call** - a sub-agent gets only a task string and returns only an answer |
# | **Use when** | the orchestrator must stay in charge and combine results; the sub-agents need clean, small contexts |
# | **Watch out** | the orchestrator only knows what the sub-agent chose to return; a vague tool description means bad delegation |
#
# This is how Claude Code, Copilot and Deep Agents do "sub-agents": a sub-agent
# is a tool whose implementation happens to be another agent. The sub-agent
# never sees the orchestrator's conversation - that isolation is what keeps its
# context small, and it is the opposite of the group chat in sample 05.
#
# ```bash
# uv run 06_maf_agent_as_tool.py --profile mock
# ```

# %%
import asyncio

from agent_framework import Agent

from genaiclass import banner, get_profile, maf_client

profile = get_profile()
client = maf_client(profile)
print(banner(profile))

# %% [markdown]
# ## Two specialists, turned into tools
#
# `as_tool()` wraps an agent as a `FunctionTool` with one string argument
# (`task`). The name and description are what the orchestrator sees - write them
# like a job ad.

# %%
researcher = Agent(client, "You are a researcher. Answer factual questions in three bullet points.",
                   name="researcher")
calculator = Agent(client, "You are a calculator. Do the arithmetic step by step, give the number.",
                   name="calculator")

research_tool = researcher.as_tool(
    name="research",
    description="Look up facts about a topic, place, product or company.",
)
math_tool = calculator.as_tool(
    name="calculate",
    description="Do arithmetic: totals, percentages, costs, unit conversions.",
)

orchestrator = Agent(
    client,
    "You are a planning assistant. Delegate facts to `research` and numbers to "
    "`calculate`, then combine their answers into one short reply.",
    name="orchestrator",
    tools=[research_tool, math_tool],
)


# %% [markdown]
# ## One question, two delegations
#
# The orchestrator's `response.messages` shows the delegation: tool calls out,
# tool results back. Each tool result is a whole sub-agent run, compressed into
# one string - which is exactly what the orchestrator gets to reason with.

# %%
async def main() -> None:
    question = ("Research the facts about Lisbon for a trip, and calculate the cost "
                "of 4 nights at 120 EUR plus 15 percent tax.")
    response = await orchestrator.run(question)

    for message in response.messages:
        for content in message.contents:
            if content.type == "function_call":
                print(f"  -> delegates to {content.name}: {str(content.arguments)[:70]}")
            elif content.type == "function_result":
                print(f"  <- result: {str(content.result)[:90]}")
    print(f"\nfinal: {response.text}")


asyncio.run(main())

# %% [markdown]
# ## Variations worth knowing
#
# * `as_tool(approval_mode="always_require")` - the orchestrator must get human
#   approval before delegating. Cheap guardrail for expensive or risky sub-agents.
# * `as_tool(propagate_session=True)` - share the orchestrator's session with the
#   sub-agent. Gives up the isolation above; use deliberately.
# * A sub-agent can be *remote*: sample 08 wraps an agent running in another
#   process (over A2A) in exactly the same way.
