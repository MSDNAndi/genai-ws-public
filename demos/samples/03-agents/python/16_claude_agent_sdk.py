# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "claude-agent-sdk==0.2.157",
# ]
# ///
# %% [markdown]
# # 16 - Claude Agent SDK (Anthropic)
#
# | | |
# |---|---|
# | **Pattern** | **harness as a library**: Claude Code's agent loop with built-in file/search/shell tools, permissions, hooks, sub-agents |
# | **Communication** | in-process **MCP** for your tools; sub-agents via a delegation tool (context isolation, like sample 06) |
# | **Use when** | the agent's job is *work on files and systems* - coding, analysis, ops - not a chat reply |
# | **Watch out** | built-in tools act on your machine: allow-list them, and put hard rules in **hooks**, not in the prompt |
#
# Everything in samples 01-15 needed *you* to write the tools. Here the agent
# arrives with Read, Glob, Grep, Edit, Write, Bash, WebSearch, WebFetch and a
# sub-agent mechanism already built in - you mostly decide what it may *not* do.
#
# Anthropic's own split is worth teaching because OpenAI and GitHub split the
# same way - **who supplies the harness** (loop + tools + context management)
# and **who supplies the deployment**:
#
# | Anthropic surface | harness | deployment |
# |---|---|---|
# | Messages API, your own loop | you | you |
# | Messages API tool runner | SDK (your tools only) | you |
# | **Claude Agent SDK** (this sample) | SDK - Claude Code, built-in tools | **you** |
# | Managed Agents | Anthropic | Anthropic (per-session sandbox) |
#
# ## Requirements - this sample does not run on the mock
#
# The SDK drives the `claude` CLI (Claude Code) as a subprocess, which talks to
# Claude, not to an OpenAI-compatible endpoint. You need Claude Code installed
# and signed in (`claude` then `/login`, or `ANTHROPIC_API_KEY`). Claude is not
# on the workshop's Foundry endpoint (Anthropic models there are Marketplace, not
# credit-eligible) - this is an instructor demo.
#
# ```bash
# uv run 16_claude_agent_sdk.py           # explains itself, calls nothing
# uv run 16_claude_agent_sdk.py --live    # real run, read-only tools, capped at $1 (~$0.50 typical)
# ```

# %%
import asyncio
import shutil
import sys
from pathlib import Path

from claude_agent_sdk import (
    AgentDefinition,
    AssistantMessage,
    ClaudeAgentOptions,
    HookMatcher,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    create_sdk_mcp_server,
    query,
    tool,
)

SAMPLES = Path(__file__).resolve().parents[1]  # samples/03-agents

if "--live" not in sys.argv:
    print("Claude Agent SDK sample - needs the `claude` CLI signed in to a Claude account.")
    print(f"  claude CLI found: {shutil.which('claude') or 'no - install Claude Code first'}")
    print("  Re-run with --live for a real run (read-only tools, capped at $1, ~$0.50 typical).")
    sys.exit(0)


# %% [markdown]
# ## 1. Your own tool, as an in-process MCP server
#
# The SDK speaks MCP for custom tools - the same protocol as Segment 2's servers,
# just without a separate process. The tool's full name becomes
# `mcp__<server>__<tool>`, and that is the name you allow-list.

# %%
@tool("get_current_weather", "Current weather conditions for one place.", {"location": str})
async def get_current_weather(args: dict) -> dict:
    return {"content": [{"type": "text", "text": f"18C and light rain in {args['location']}"}]}


workshop_tools = create_sdk_mcp_server(name="workshop", tools=[get_current_weather])


# %% [markdown]
# ## 2. A hook is a guardrail the model cannot argue with
#
# `PreToolUse` runs before every tool call. Returning `permissionDecision:
# "deny"` blocks the call, and the reason goes back to the model. "Never read
# .env files" in the system prompt is a request; this is a rule.
#
# The second rule was learned from a live run: allow-listing *tools* does not
# confine *paths*. With only Read/Grep allowed, a sub-agent still went reading
# inside `.venv/site-packages` and the repo root. So the hook also pins every
# path to this folder. The same hook doubles as an audit log.

# %%
def deny(reason: str) -> dict:
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                   "permissionDecision": "deny",
                                   "permissionDecisionReason": reason}}


async def audit_and_protect(hook_input: dict, tool_use_id, context) -> dict:
    name, args = hook_input.get("tool_name"), hook_input.get("tool_input", {})
    print(f"  [hook] {name} {str(args)[:90]}")
    for key in ("file_path", "path"):
        if key in args:
            target = (SAMPLES / args[key]).resolve()   # relative paths resolve against cwd
            if ".env" in target.name:
                return deny("Secrets files are off limits.")
            if not target.is_relative_to(SAMPLES):
                return deny(f"Only files under {SAMPLES.name}/ may be accessed.")
    return {}


# %% [markdown]
# ## 3. A sub-agent with its own, smaller toolset
#
# The main agent can delegate to `reviewer`. The sub-agent runs in its own
# context (it does not see the main conversation) and only has Read/Grep -
# the same isolation idea as sample 06, built into the harness. The delegation
# tool is called `Agent` (older docs say `Task`); calls made *inside* a
# sub-agent carry a `parent_tool_use_id`, which is how the output below marks them.

# %%
options = ClaudeAgentOptions(
    model="claude-opus-5",
    cwd=str(SAMPLES),
    system_prompt="You are a code reviewer for a workshop repo. Be concise.",
    mcp_servers={"workshop": workshop_tools},
    # Allow-list: read-only built-ins, our MCP tool, and the delegation tool.
    allowed_tools=["Read", "Glob", "Grep", "mcp__workshop__get_current_weather", "Agent"],
    permission_mode="dontAsk",      # anything not allow-listed is refused, never prompted
    agents={"reviewer": AgentDefinition(
        description="Reviews one sample file and names its single biggest weakness.",
        prompt="You review one Python sample. Reply with one sentence.",
        tools=["Read", "Grep"],
    )},
    hooks={"PreToolUse": [HookMatcher(hooks=[audit_and_protect])]},
    max_turns=12,
    max_budget_usd=1.00,            # hard cap; a verified run on Opus 5 cost ~$0.50
)

TASK = (
    "1) Use Glob to count the Python samples under python/. "
    "2) Try to read ../../.env and report what happens. "
    "3) Ask the reviewer sub-agent about python/06_maf_agent_as_tool.py. "
    "4) Get the weather in Lisbon. Then summarise all four in four lines."
)


# %% [markdown]
# ## Run it and watch the harness work
#
# `query` streams messages: the assistant's text and tool calls, then a final
# `ResultMessage` with turns and cost - the numbers you would alert on in
# production. Expect one tool you did not allow-list: `ToolSearch`. The harness
# loads MCP tool schemas lazily, only when the model asks for them - that is
# how Claude Code keeps large tool catalogues out of the context window.

# %%
async def main() -> None:
    async for message in query(prompt=TASK, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    who = " (sub-agent)" if message.parent_tool_use_id else ""
                    print(f"  -> tool {block.name}{who}")
                elif isinstance(block, TextBlock) and not message.parent_tool_use_id:
                    print(block.text)
        elif isinstance(message, ResultMessage):
            print(f"\n[{message.subtype}] turns={message.num_turns} "
                  f"cost=${message.total_cost_usd or 0:.4f} denials={len(message.permission_denials or [])}")


asyncio.run(main())

# %% [markdown]
# ## Where this goes next
#
# * **Managed Agents** is the hosted version: Anthropic runs the loop *and* a
#   per-session sandbox, with persisted agent configs, schedules and outcomes.
#   (Not on Foundry; Anthropic's platform.)
# * The same harness is in a Foundry hosted agent (sample 12's container accepts
#   Claude Agent SDK code) - you supply the deployment, Foundry the identity.
# * `setting_sources=["project"]` is documented to load the repo's `CLAUDE.md`,
#   skills and commands, so the SDK agent follows the same house rules as
#   Claude Code does. (Not exercised in this sample.)
