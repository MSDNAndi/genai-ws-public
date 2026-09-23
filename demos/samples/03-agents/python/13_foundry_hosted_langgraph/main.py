# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "genaiclass",
#     "langchain==1.4.2",
#     "langchain-openai==1.6.2",
#     "langgraph==1.2.11",
#     "langchain-azure-ai[hosting]==1.2.10",
#     "azure-identity==1.25.3",
# ]
#
# [tool.uv.sources]
# genaiclass = { path = "../../../../shared/python", editable = true }
# ///
# %% [markdown]
# # 13 - A Foundry hosted agent (LangGraph)
#
# | | |
# |---|---|
# | **Pattern** | sample 12 again, with a **different framework inside the same kind of container** |
# | **Communication** | the Responses protocol over HTTP - identical from the outside |
# | **Use when** | your team is on LangChain/LangGraph but wants Foundry's identity, sessions and scaling |
# | **Watch out** | the graph is found through `langgraph.json`, not through code - keep the two in sync |
#
# This is the "beyond one vendor's framework" punchline of the segment: Foundry
# hosts MAF (sample 12), LangGraph (here), OpenAI Agents SDK, Claude Agent SDK
# or your own code the same way, and `14_call_hosted_agent.py` cannot tell
# which one it is talking to.
#
# ```bash
# uv run main.py --profile mock      # serves http://localhost:8088/responses
# uv run ../14_call_hosted_agent.py  # second terminal - same client as sample 12
# ```
#
# Deploy: `azd ai agent init -m azure.yaml` then `azd up` (see ../12_foundry_hosted_maf/README.md).

# %%
import os
import sys

from langchain.agents import create_agent
from langchain_core.tools import tool


@tool
def get_current_weather(location: str) -> dict:
    """Current weather conditions for one place."""
    return {"location": location, "temperature_c": 18, "conditions": "light rain"}


# %% [markdown]
# ## One model, two runtimes
#
# Hosted: the platform injects `FOUNDRY_PROJECT_ENDPOINT`; the project's OpenAI
# client is authenticated with the agent's own Entra identity (a token provider,
# never a key). Local: the repo's provider profiles.

# %%
def build_model():
    if os.environ.get("FOUNDRY_PROJECT_ENDPOINT"):
        from azure.ai.projects import AIProjectClient
        from azure.identity import DefaultAzureCredential, get_bearer_token_provider
        from langchain_openai import ChatOpenAI

        credential = DefaultAzureCredential()
        project = AIProjectClient(endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
                                  credential=credential)
        return ChatOpenAI(
            model=os.environ["AZURE_AI_MODEL_DEPLOYMENT_NAME"],
            base_url=str(project.get_openai_client().base_url),
            api_key=get_bearer_token_provider(credential, "https://ai.azure.com/.default"),
            use_responses_api=True,
            output_version="responses/v1",
        )

    from genaiclass import banner, get_profile, langchain_model

    profile = get_profile()
    print(f"local mode: {banner(profile)}")
    return langchain_model(profile)


# %% [markdown]
# ## The export the platform looks for
#
# `langgraph.json` maps the name `agent` to `./main.py:graph`. The hosting
# runner imports this module and serves whatever `graph` is - any compiled
# LangGraph graph, including the supervisor from sample 10.

# %%
graph = create_agent(
    build_model(),
    tools=[get_current_weather],
    system_prompt="You are a travel assistant. Use the tools; never guess numbers. Be brief.",
    name="travel-agent",
)

# %% [markdown]
# ## Serve it
#
# In the container the entrypoint is
# `python -m langchain_azure_ai.agents.hosting.run --protocol responses`.
# Running this file directly does the same, so local and hosted stay identical.

# %%
if __name__ == "__main__":
    from langchain_azure_ai.agents.hosting import run

    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, here)  # so the runner can import ./main.py:graph
    run.main(["--protocol", "responses", "--config", os.path.join(here, "langgraph.json")])
