# Deploying the hosted agents to Microsoft Foundry

Applies to all three hosted samples - they differ only in the framework inside:

| Folder | Framework | Entry point |
|---|---|---|
| `python/12_foundry_hosted_maf/` | Microsoft Agent Framework | `python main.py` |
| `python/13_foundry_hosted_langgraph/` | LangGraph | `python -m langchain_azure_ai.agents.hosting.run --protocol responses` |
| `csharp/12_foundry_hosted_maf/` | Microsoft Agent Framework (.NET) | `dotnet HostedTravelAgent.dll` |

**Nothing here has been deployed yet** - the deployment files follow Microsoft's
verified samples (`microsoft-foundry/foundry-samples`, checked 2026-09-21), and
the agents themselves are tested locally against the mock. Expect to find one
or two real-world details on the first deploy.

## Prerequisites

* A Foundry project in a [hosted-agent region](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/hosted-agents#region-availability)
  (West Europe, Sweden Central, Germany West Central, East US 2, ...).
* Role **Foundry Project Manager** on the project (renamed from Azure AI Project Manager).
* Azure Developer CLI `azd` >= 1.27.1 with the agents extension:
  `azd extension install azure.ai.agents`
* No local Docker needed: `azd` builds the image remotely in Azure Container Registry.

## Local first (no Azure)

```bash
uv run main.py --profile mock          # or: azd ai agent run
uv run ../14_call_hosted_agent.py      # or: azd ai agent invoke --local "Hi"
```

## Deploy

```bash
azd ai agent init -m azure.yaml    # once: pick subscription, project, model
azd up                             # provision + build in ACR + create agent version
azd ai agent show                  # name, version, status
azd ai agent invoke "What is the weather in Lisbon?"
```

`azure.yaml` declares a `gpt-5.4-mini` deployment (copied from Microsoft's
sample). To reuse the workshop's shared deployment instead, delete the
`deployments:` block and set `AZURE_AI_MODEL_DEPLOYMENT_NAME` to its name.

## Call it from code

```bash
export FOUNDRY_PROJECT_ENDPOINT=https://<account>.services.ai.azure.com/api/projects/<project>
az login
uv run ../14_call_hosted_agent.py --agent travel-agent-maf
```

That is `AIProjectClient(...).get_openai_client(agent_name=...)` - an ordinary
OpenAI client, authenticated with your Entra token. There is no API key for a
hosted agent, by design.

## What the platform gives you

* its own **Entra identity** per agent - `DefaultAzureCredential()` inside the
  container resolves to it; no secrets in the image or in env vars
* a **VM-isolated sandbox per session**, persistent `$HOME`, idle timeout 2-60
  min (default 15), scale to zero
* `FOUNDRY_PROJECT_ENDPOINT`, `FOUNDRY_AGENT_NAME`, `APPLICATIONINSIGHTS_CONNECTION_STRING`
  injected automatically (the `FOUNDRY_*` prefix is reserved)
* Responses endpoint `{project}/agents/{name}/endpoint/protocols/openai/responses`,
  plus A2A and publishing to Teams / Microsoft 365
* immutable **versions**; each `azd deploy` creates a new one

## Clean up

```bash
azd down
```

Compute is billed per active session (CPU + memory); an idle agent costs
nothing, but the provisioned project, registry and model deployment do.
