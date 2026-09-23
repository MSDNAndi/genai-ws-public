# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "openai==3.16.2",
#     "azure-ai-projects==2.7.0",
#     "azure-identity==1.25.3",
# ]
# ///
# %% [markdown]
# # 14 - Calling a hosted agent
#
# | | |
# |---|---|
# | **Pattern** | client of an agent service |
# | **Communication** | **Responses protocol**: `responses.create`, conversation chained with `previous_response_id` |
# | **Use when** | any app, script, or other agent that needs to use a hosted agent |
# | **Watch out** | locally there is no auth; in Foundry every call carries an Entra token - never an API key |
#
# The agent in sample 12 (MAF) or 13 (LangGraph) looks exactly like the OpenAI
# Responses API from the outside. So the client is the plain `openai` SDK - the
# same `responses.create` you met in `01-foundations/06`. Whatever framework is
# inside the container is invisible here, which is the whole idea.
#
# ```bash
# uv run 14_call_hosted_agent.py                      # local: http://localhost:8088
# uv run 14_call_hosted_agent.py --agent travel-agent-maf   # deployed, needs:
#     FOUNDRY_PROJECT_ENDPOINT=https://<acct>.services.ai.azure.com/api/projects/<project>
#     and `az login` (DefaultAzureCredential)
# ```

# %%
import argparse
import os

from openai import OpenAI

parser = argparse.ArgumentParser()
parser.add_argument("--agent", help="deployed agent name; omit to call localhost:8088")
parser.add_argument("--url", default="http://localhost:8088", help="local agent base URL")
args, _ = parser.parse_known_args()


# %% [markdown]
# ## Connect: the only line that differs between laptop and cloud
#
# Deployed: `AIProjectClient.get_openai_client(agent_name=...)` returns an OpenAI
# client already pointed at `{project}/agents/{name}/endpoint/protocols/openai`
# and authenticated with your Entra token. Local: a plain client at port 8088.

# %%
def connect() -> OpenAI:
    if args.agent:
        from azure.ai.projects import AIProjectClient
        from azure.identity import DefaultAzureCredential

        project = AIProjectClient(endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
                                  credential=DefaultAzureCredential())
        print(f"calling deployed agent '{args.agent}'")
        return project.get_openai_client(agent_name=args.agent)

    print(f"calling local agent at {args.url}")
    return OpenAI(base_url=args.url, api_key="local-no-auth")


client = connect()

# %% [markdown]
# ## Two turns, no history sent
#
# Turn 2 sends only the new question plus the id of turn 1. The hosting platform
# looks the conversation up - compare with Chat Completions, where you resend
# every message every time.

# %%
first = client.responses.create(input="What is the weather in Lisbon?")
print(f"turn 1 [{first.id[:24]}...]: {first.output_text}")

for item in first.output:  # the agent's work is visible, not just its answer
    if item.type in ("function_call", "function_call_output"):
        print(f"  - {item.type}: {getattr(item, 'name', '') or str(getattr(item, 'output', ''))[:60]}")

second = client.responses.create(input="And should I pack an umbrella?",
                                 previous_response_id=first.id)
print(f"turn 2: {second.output_text}")

# %% [markdown]
# ## Streaming
#
# `stream=True` gives server-sent events. The text arrives as
# `response.output_text.delta` events - the same event types as calling
# OpenAI directly. (Use `create(stream=True)`, not the `responses.stream()`
# helper: the helper insists on a `model` argument, and a hosted agent has none -
# the agent decides which model it uses.)

# %%
print("streamed: ", end="")
for event in client.responses.create(input="Say hello in five words.", stream=True):
    if event.type == "response.output_text.delta":
        print(event.delta, end="", flush=True)
print()
