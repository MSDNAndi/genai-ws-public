# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "genaiclass",
#     "agent-framework-core==1.19.0",
#     "agent-framework-openai==1.14.4",
#     "agent-framework-foundry==1.13.1",
#     "agent-framework-foundry-hosting==1.0.0b260918",
# ]
#
# [tool.uv.sources]
# genaiclass = { path = "../../../../shared/python", editable = true }
# ///
# %% [markdown]
# # 12 - A Foundry hosted agent (Microsoft Agent Framework)
#
# | | |
# |---|---|
# | **Pattern** | the same agent as sample 01, **deployed**: Foundry runs your container per session |
# | **Communication** | the **Responses protocol over HTTP** - any OpenAI SDK is a client; Foundry adds A2A and Teams |
# | **Use when** | the agent must be a service: identity, scaling, sessions, telemetry, versioning |
# | **Watch out** | never bake keys into the image - the platform gives the agent its own Entra identity |
#
# Everything so far ran inside your script. A hosted agent is the step from
# "code on my laptop" to "a service other people call". Foundry Agent Service
# (hosted agents GA, Sept 2026) takes your container and gives it an endpoint, a
# dedicated Entra identity, a VM-isolated sandbox **per session** with a
# persistent `$HOME`, scale to zero, and Application Insights tracing.
#
# The framework is your choice - sample 13 hosts a LangGraph agent the same way.
#
# ## Run it locally (no Azure, no Docker)
#
# ```bash
# uv run main.py --profile mock          # serves http://localhost:8088/responses
# uv run ../14_call_hosted_agent.py      # in a second terminal
# ```
#
# ## Deploy it (needs a Foundry project; see README.md in this folder)
#
# ```bash
# azd ai agent init -m azure.yaml   # once
# azd up                            # provision + build in ACR + deploy
# azd ai agent invoke "Hi"
# ```

# %%
import os
from typing import Annotated

from agent_framework import Agent, tool
from agent_framework_foundry_hosting import ResponsesHostServer
from pydantic import Field


@tool
def get_current_weather(location: Annotated[str, Field(description="City and region")]) -> dict:
    """Current weather conditions for one place."""
    return {"location": location, "temperature_c": 18, "conditions": "light rain"}


# %% [markdown]
# ## One agent, two runtimes
#
# The only branch in the file. **Hosted:** the platform injects
# `FOUNDRY_PROJECT_ENDPOINT`, and `DefaultAzureCredential` resolves to the agent's
# own Entra identity - no key exists anywhere. **Local:** fall back to the repo's
# provider profiles, so the identical agent runs against the mock or Ollama.

# %%
def build_agent() -> Agent:
    instructions = "You are a travel assistant. Use the tools; never guess numbers. Be brief."

    if os.environ.get("FOUNDRY_PROJECT_ENDPOINT"):
        from agent_framework.foundry import FoundryChatClient
        from azure.identity import DefaultAzureCredential

        client = FoundryChatClient(
            project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
            model=os.environ["AZURE_AI_MODEL_DEPLOYMENT_NAME"],
            credential=DefaultAzureCredential(),
        )
        # The hosting platform stores the conversation, so the model service must not.
        return Agent(client, instructions, name="travel-agent", tools=[get_current_weather],
                     default_options={"store": False})

    from genaiclass import banner, get_profile, maf_client

    profile = get_profile()
    print(f"local mode: {banner(profile)}")
    return Agent(maf_client(profile), instructions, name="travel-agent",
                 tools=[get_current_weather])


# %% [markdown]
# ## Serve it
#
# `ResponsesHostServer` is the adapter from `agent-framework-foundry-hosting`:
# it exposes `POST /responses` (OpenAI-compatible, streaming via SSE),
# `GET /readiness` for the platform's health probe, and OpenTelemetry. Port 8088
# is the platform contract. Multi-turn works through `previous_response_id` -
# the client never resends history.

# %%
if __name__ == "__main__":
    ResponsesHostServer(build_agent()).run(port=int(os.environ.get("PORT", "8088")))
