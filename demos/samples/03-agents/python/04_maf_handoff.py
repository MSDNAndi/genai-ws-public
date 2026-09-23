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
# # 04 - Handoff (triage and routing)
#
# | | |
# |---|---|
# | **Pattern** | handoff: an agent decides who should own the conversation next |
# | **Communication** | **control transfer** - the model calls a `handoff_to_<agent>` tool, and the target takes over the whole conversation |
# | **Use when** | customer-service shapes: triage -> specialist, escalation, "let me put you through" |
# | **Watch out** | routing is a model decision, so it can be wrong; and a handoff is *conversational* - it hands back to the user after every turn |
#
# Contrast with sample 06 (agent-as-tool): there the orchestrator *keeps*
# control and gets an answer back. Here control *moves*, and the triage agent is
# out of the loop until someone hands back to it.
#
# ```bash
# uv run 04_maf_handoff.py --profile mock
# ```

# %%
import asyncio

from agent_framework import Agent
from agent_framework.orchestrations import HandoffAgentUserRequest, HandoffBuilder

from genaiclass import banner, get_profile, maf_client

profile = get_profile()
client = maf_client(profile)
print(banner(profile))


# %% [markdown]
# ## The agents
#
# `description` matters here more than anywhere: it becomes the description of
# the `handoff_to_<name>` tool the triage agent sees, i.e. it is the routing rule.
#
# `require_per_service_call_history_persistence=True` is mandatory for handoff
# participants since 2026 (the builder refuses to build without it). Handoff
# short-circuits tool calls, and this keeps each agent's local history consistent
# with what the model service actually saw.

# %%
def specialist(name: str, instructions: str, description: str) -> Agent:
    return Agent(client, instructions, name=name, description=description,
                 require_per_service_call_history_persistence=True)


def build_workflow():
    triage = specialist("triage", "You are the front desk. Route every request to the right team.",
                        "Front desk that routes requests")
    billing = specialist("billing", "You are billing support. Resolve invoice and payment issues.",
                         "Billing: invoices, payments, refunds, charges")
    tech = specialist("tech", "You are technical support. Resolve login, error and outage issues.",
                      "Technical: login problems, errors, outages, bugs")
    return (HandoffBuilder(participants=[triage, billing, tech])
            .with_start_agent(triage)
            .add_handoff(triage, [billing, tech])   # triage may route to either specialist
            .add_handoff(billing, [triage])         # specialists may hand back ...
            .add_handoff(tech, [triage])            # ... but not sideways to each other
            .build())


# %% [markdown]
# ## Running a conversation that pauses for the user
#
# After an agent answers, the workflow emits a `request_info` event carrying a
# `HandoffAgentUserRequest` - "what does the user say next?". You answer it by
# running again with `responses={request_id: ...}`. That is human-in-the-loop by
# construction.
#
# The user here is scripted so the sample runs unattended: one follow-up, then
# `terminate()`.

# %%
SCRIPTED_USER = ["The charge appears twice, on the 3rd and the 4th."]


async def converse() -> None:
    workflow = build_workflow()
    replies = iter(SCRIPTED_USER)
    stream = workflow.run("My invoice looks wrong.", stream=True)

    while stream is not None:
        pending: dict = {}
        speaker = None
        async for event in stream:
            if event.type == "output":
                if event.executor_id != speaker:
                    speaker = event.executor_id
                    print(f"\n[{speaker}] ", end="")
                print(getattr(event.data, "text", "") or "", end="", flush=True)
            elif event.type == "request_info" and isinstance(event.data, HandoffAgentUserRequest):
                pending[event.request_id] = event.data
        print()

        if not pending:
            break
        request_id, request = next(iter(pending.items()))
        reply = next(replies, None)
        if reply is None:
            print("[user] (ends the conversation)")
            stream = workflow.run(responses={request_id: request.terminate()}, stream=True)
            async for _ in stream:
                pass
            break
        print(f"[user] {reply}")
        stream = workflow.run(responses={request_id: request.create_response(reply)}, stream=True)


asyncio.run(converse())

# %% [markdown]
# ## Reading the output
#
# `[triage]` speaks first and its turn is a tool call (`handoff_to_billing`), so
# you mostly see `[billing]` answer - the triage agent has left the room. When
# the user replies, the reply goes to **billing**, not back to triage: the
# conversation now belongs to whoever received the handoff.
#
# Offline, the mock server routes by keyword overlap with the `description`
# fields ("invoice" -> billing). A real model does the same job with judgement,
# and gets it wrong in the same ways a bad description invites.
