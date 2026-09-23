# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "genaiclass",
#     "agent-framework-core==1.19.0",
#     "agent-framework-openai==1.14.4",
#     "agent-framework-orchestrations==1.2.0",
#     "agent-framework-a2a==1.0.0b260918",
#     "a2a-sdk==1.1.5",
#     "uvicorn==0.53.0",
#     "starlette==1.6.0",
#     "sse-starlette==3.4.11",
# ]
#
# [tool.uv.sources]
# genaiclass = { path = "../../../shared/python", editable = true }
# ///
# %% [markdown]
# # 08 - Agent-to-agent over the network (A2A)
#
# | | |
# |---|---|
# | **Pattern** | remote agent: an agent in another process, team, language or vendor, used as a participant |
# | **Communication** | **a network protocol** - [A2A](https://a2a-protocol.org) v1.0: discovery via an agent card, JSON-RPC calls, tasks |
# | **Use when** | the other agent is owned by someone else, or written in another framework, or must scale separately |
# | **Watch out** | every hop is a network call: latency, auth, versioning and "who is responsible for this answer" all become real |
#
# MCP connects an agent to **tools and data**. A2A connects an agent to **another
# agent** - something with its own reasoning, that you cannot see inside. Both are
# vendor-neutral, both are Linux Foundation projects, and Foundry hosted agents
# (sample 12) speak A2A out of the box.
#
# To stay one file, this sample starts the "remote" agent in a background thread.
# In real life it is a different deployment, possibly not even Python.
#
# ```bash
# uv run 08_maf_a2a.py --profile mock
# ```
#
# `agent-framework-a2a` is **beta** (1.0.0b260918). A2A the protocol is 1.0 GA.

# %%
import asyncio
import threading
import time

import uvicorn
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill
from agent_framework import Agent
from agent_framework.a2a import A2AAgent, A2AExecutor
from agent_framework.orchestrations import SequentialBuilder
from starlette.applications import Starlette

from genaiclass import banner, get_profile, maf_client

profile = get_profile()
client = maf_client(profile)
print(banner(profile))

PORT = 9999
URL = f"http://127.0.0.1:{PORT}/"

# %% [markdown]
# ## Side A - publish an agent
#
# Two things go on the wire:
#
# * the **agent card** at `/.well-known/agent-card.json` - name, description,
#   skills, endpoint. This is how another agent *discovers* what you can do;
# * a **JSON-RPC endpoint** that accepts messages and returns tasks.
#
# `A2AExecutor` is the adapter: it turns A2A requests into `agent.run` calls and
# the responses back into A2A events. Nothing about the agent itself changes.

# %%
# Its own client, not the shared one: the server runs on a different thread and
# event loop, and an async HTTP client cannot be shared across loops. In a real
# deployment this is simply a different process with its own configuration.
fx_agent = Agent(maf_client(profile),
                 "You are a currency expert. Convert amounts and name the rate you used.",
                 name="fx")

card = AgentCard(
    name="fx",
    description="Converts amounts between currencies.",
    version="1.0.0",
    default_input_modes=["text"],
    default_output_modes=["text"],
    capabilities=AgentCapabilities(streaming=False),
    supported_interfaces=[AgentInterface(url=URL, protocol_binding="JSONRPC")],
    skills=[AgentSkill(id="convert", name="convert", description="Currency conversion",
                       tags=["finance"])],
)
handler = DefaultRequestHandler(agent_executor=A2AExecutor(fx_agent),
                                task_store=InMemoryTaskStore(), agent_card=card)
app = Starlette(routes=[*create_agent_card_routes(card), *create_jsonrpc_routes(handler, "/")])

server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="warning"))
threading.Thread(target=server.run, daemon=True).start()
while not server.started:
    time.sleep(0.1)
print(f"remote agent 'fx' published at {URL} (card: {URL}.well-known/agent-card.json)")


# %% [markdown]
# ## Side B - use it as if it were local
#
# `A2AAgent(url=...)` fetches the card and gives you an object with the same
# `run` method as every other agent. That uniformity is the point: a remote agent
# drops into a sequential pipeline (below), a concurrent panel, or `.as_tool()`
# for a supervisor (sample 06), without the orchestration code knowing it is remote.

# %%
async def main() -> None:
    remote_fx = A2AAgent(name="fx", url=URL)

    print("\n--- 1. direct call over A2A")
    response = await remote_fx.run("Convert 250 EUR to USD.")
    print(f"  {response.text}")

    print("\n--- 2. remote agent as one step of a local pipeline")
    planner = Agent(client, "You are a trip planner. State the budget in EUR for 3 nights.",
                    name="planner")
    pipeline = SequentialBuilder(participants=[planner, remote_fx]).build()
    result = await pipeline.run("Plan a weekend in New York.")
    for message in result.get_outputs()[-1].messages:
        print(f"  [{message.author_name or message.role}] {message.text[:100]}")


asyncio.run(main())
server.should_exit = True

# %% [markdown]
# ## What crossed the wire
#
# Compare the context counter with sample 02. In a local sequential pipeline
# every agent is sent the *whole* conversation. Here the remote agent's model
# saw exactly one incoming message - the planner's reply - because A2A carries
# **messages**, not your local transcript. If the remote agent needs context,
# you must put it in the message. That is the right default across a trust
# boundary (you do not ship your whole conversation to someone else's agent),
# and a common surprise the first time a pipeline goes remote.
