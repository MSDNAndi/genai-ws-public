# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "genaiclass",
#     "github-copilot-sdk==1.0.14",
# ]
#
# [tool.uv.sources]
# genaiclass = { path = "../../../shared/python", editable = true }
# ///
# %% [markdown]
# # 17 - GitHub Copilot SDK
#
# | | |
# |---|---|
# | **Pattern** | **harness as a library**: the Copilot CLI's planner, tool loop and built-in tools, embedded in your app |
# | **Communication** | a session with an **event stream**; your tools and hooks are called back over the SDK's RPC channel |
# | **Use when** | you want Copilot's agent (and its GitHub integration) inside your own tool, CI job or service |
# | **Watch out** | it arrives with file/shell/GitHub tools switched on - restrict `available_tools` explicitly |
#
# How GitHub "does agents", in one table - the same harness shows up everywhere:
#
# | Surface | Where it runs | You write |
# |---|---|---|
# | Copilot in VS Code / JetBrains (agent mode) | your editor | prompts, `AGENTS.md`, `.github/agents/*.agent.md` |
# | Copilot CLI | your terminal | the same files |
# | Copilot coding agent | GitHub's cloud; assign it an issue, it opens a PR | the same files + a setup workflow |
# | **Copilot SDK** (this sample, GA 2026-06) | **your process** (Python, Node, .NET, Go) | code |
#
# The surprise worth showing: **bring your own model**. Point `provider` at any
# OpenAI-compatible endpoint and Copilot's harness runs on it - the workshop's
# Foundry endpoint, Ollama, or the offline mock - with **no GitHub sign-in**.
# Without `provider`, it uses your Copilot subscription's models instead.
#
# ```bash
# uv run 17_github_copilot_sdk.py --profile mock
# ```
#
# First run downloads the Copilot runtime (it does not use a `copilot` CLI on
# your PATH - here that was 0.0.350, the SDK started its own 1.0.85).

# %%
import asyncio
from pathlib import Path

from copilot import CopilotClient, ProviderConfig, SessionHooks, define_tool
from copilot.generated.rpc import PermissionDecisionApproveOnce, PermissionDecisionReject
from pydantic import BaseModel, Field

from genaiclass import banner, get_profile

profile = get_profile()
print(banner(profile))


# %% [markdown]
# ## A tool of your own
#
# `define_tool` builds the schema from a Pydantic model. Like every tool, its
# calls go through the permission handler below.

# %%
class WeatherParams(BaseModel):
    location: str = Field(description="City and region")


@define_tool(description="Current weather conditions for one place.")
def get_current_weather(params: WeatherParams) -> str:
    return f"18C and light rain in {params.location}"


# %% [markdown]
# ## Hooks and permissions: the same two guardrails as Claude's SDK
#
# * `on_pre_tool_use` sees every call first - audit it, rewrite its arguments
#   (`modifiedArgs`) or deny it (`permissionDecision: "deny"`).
# * `on_permission_request` answers "may this tool do this?" for anything that
#   needs approval. The policy here: our own tools yes (`custom-tool`),
#   everything built in (shell, file writes, GitHub API) no.
#
# Trap (verified on 1.0.14): a hook that returns `permissionDecision: "allow"`
# **pre-approves the call and the permission handler is never asked**. An
# "audit" hook that answers "allow" quietly grants everything. Observe-only
# hooks must return no decision at all, as below.

# %%
def audit(hook_input, *_) -> dict:
    print(f"  [hook] {hook_input['toolName']} {str(hook_input['toolArgs'])[:80]}")
    return {}   # observe only: no decision, so the normal permission flow still applies


def own_tools_only(request, *_):
    kind = getattr(request, "kind", "?")
    if kind == "custom-tool":
        print(f"  [permission] approved: {kind}")
        return PermissionDecisionApproveOnce()
    print(f"  [permission] refused: {kind}")
    return PermissionDecisionReject(feedback="Unattended run: only our own tools are allowed.")


# %% [markdown]
# ## One session on the workshop's model
#
# `provider` is the whole BYOK story: `type="openai"` + `wire_api="completions"`
# means "any Chat Completions endpoint". `available_tools` switches the built-in
# catalogue off except for what you list.

# %%
async def main() -> None:
    client = CopilotClient(working_directory=str(Path(__file__).parent))
    await client.start()
    status = await client.get_status()
    print(f"Copilot runtime {status.version}")
    try:
        session = await client.create_session(
            model=profile.model,
            provider=ProviderConfig(type="openai", wire_api="completions",
                                    base_url=profile.base_url, api_key=profile.api_key,
                                    headers=profile.headers or None),
            tools=[get_current_weather],
            available_tools=["get_current_weather"],
            hooks=SessionHooks(on_pre_tool_use=audit),
            on_permission_request=own_tools_only,
        )
        reply = await session.send_and_wait("What is the weather in Lisbon?", timeout=120)
        print(f"\nanswer: {reply.data.content if reply else '(no reply)'}")

        # The session is an event log - the same stream a UI renders.
        kinds = [str(getattr(event, 'type', type(event).__name__)) for event in await session.get_events()]
        print(f"\n{len(kinds)} session events, e.g.: {sorted(set(kinds))[:8]}")
    finally:
        await client.stop()


asyncio.run(main())

# %% [markdown]
# ## Where this goes next
#
# * Drop the `provider` argument to use Copilot's own models (needs a Copilot
#   plan and `gh auth login` / Copilot CLI sign-in) - same code otherwise.
# * Custom agents written as `.github/agents/<name>.agent.md` are meant to be
#   picked up by Copilot in the editor, the CLI and the cloud coding agent -
#   one agent definition, several runtimes. (Documented by GitHub; not
#   exercised in this sample.)
# * Microsoft Agent Framework announced a Copilot SDK integration at Build 2026,
#   so a Copilot session can join the orchestrations in samples 02-06.
#   (Preview; not exercised here.)
