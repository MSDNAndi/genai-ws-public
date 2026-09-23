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
# # 07 - An explicit workflow graph
#
# | | |
# |---|---|
# | **Pattern** | graph / state machine: you draw the nodes and edges, including conditional branches |
# | **Communication** | **typed messages along edges** - each node sends a value of a declared type to the next |
# | **Use when** | the process is known and must be auditable; only *some* steps need a model |
# | **Watch out** | more code than an orchestration builder; that is the price of determinism |
#
# Samples 02-05 used prebuilt shapes. This one builds the graph by hand, and
# mixes plain-code nodes with an agent node. Most production "agent systems" look
# like this: a deterministic spine, with a model called only where judgement is
# actually needed. The model does not decide the control flow here - your
# `Case` conditions do.
#
# ```bash
# uv run 07_maf_workflow_graph.py --profile mock
# ```
#
# ```
#                 +--> [urgent]  (code)  ---> output
#   [classify] ---+
#     (code)      +--> [draft_reply] (agent) -> output
# ```

# %%
import asyncio
import re
from dataclasses import dataclass

from agent_framework import Agent, Case, Default, WorkflowBuilder, WorkflowContext, executor

from genaiclass import banner, get_profile, maf_client

profile = get_profile()
client = maf_client(profile)
print(banner(profile))


# %% [markdown]
# ## The message type that travels along the edges
#
# Declaring it is the point: `classify` promises to send a `Ticket`, the next
# nodes promise to accept one. The workflow validates the wiring when it is
# built, so a mismatch fails at startup, not in production at 3 a.m.

# %%
@dataclass
class Ticket:
    text: str
    urgent: bool


# %% [markdown]
# ## Nodes: two plain functions and one agent
#
# `@executor` turns a function into a node. `ctx.send_message` passes a value
# down the outgoing edge; `ctx.yield_output` produces a workflow result.

# %%
@executor(id="classify")
async def classify(text: str, ctx: WorkflowContext[Ticket]) -> None:
    # Deterministic and free. Swap in a small classifier model if rules stop scaling.
    urgent = bool(re.search(r"\b(outage|down|urgent|security|breach)\b", text, re.I))
    await ctx.send_message(Ticket(text=text, urgent=urgent))


@executor(id="urgent")
async def escalate(ticket: Ticket, ctx: WorkflowContext[None, str]) -> None:
    # No model on the urgent path: it must be fast, predictable and paged to a human.
    await ctx.yield_output(f"PAGED ON-CALL: {ticket.text}")


replier = Agent(client, "You are a support agent. Draft a two-sentence friendly reply.",
                name="draft_reply")


@executor(id="draft_reply")
async def draft_reply(ticket: Ticket, ctx: WorkflowContext[None, str]) -> None:
    response = await replier.run(ticket.text)
    await ctx.yield_output(f"DRAFT: {response.text}")


# %% [markdown]
# ## Edges: the control flow is data, not a prompt
#
# `add_switch_case_edge_group` routes on the message: first matching `Case`
# wins, `Default` catches the rest. Other edge kinds: `add_edge` (always),
# `add_fan_out_edges` / `add_fan_in_edges` (parallel branches, as in sample 03).

# %%
def build_workflow():
    return (
        WorkflowBuilder(start_executor=classify)
        .add_switch_case_edge_group(classify, [
            Case(condition=lambda t: t.urgent, target=escalate),
            Default(target=draft_reply),
        ])
        .build()
    )


async def main() -> None:
    for text in ("Our whole site is down since 09:00!", "How do I change my invoice address?"):
        result = await build_workflow().run(text)
        print(f"{text:<40} -> {result.get_outputs()[-1][:90]}")


asyncio.run(main())
