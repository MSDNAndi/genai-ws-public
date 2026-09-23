# Segment 3 - The world of agents

*A loop, a runtime, then a team.* Every sample here is the tool-calling loop
from `01-foundations/04_tool_calling` plus a decision about **who talks to whom,
how, and who is in charge**. That decision - not the framework - is what
changes between the samples, so each one opens with the same four lines:
**Pattern · Communication · Use when · Watch out**.

All versions verified on 2026-09-21. Everything runs offline against the mock
server (`uv run tools/mock_server.py`) - including the hosted agents and GitHub's
Copilot harness - except sample 16, which needs a signed-in Claude Code.

## The map

| # | Sample | Framework | Orchestration pattern | Communication pattern | Py | C# |
|---|---|---|---|---|:-:|:-:|
| 01 | `maf_agent` | MAF | single agent + tools + memory | request/response, **session** state | ✓ | ✓ |
| 02 | `maf_sequential` | MAF | **sequential** pipeline | conversation **handed down the chain** | ✓ | ✓ |
| 03 | `maf_concurrent` | MAF | **concurrent** fan-out / fan-in | **broadcast** in, **aggregate** out; agents isolated | ✓ | ✓ |
| 04 | `maf_handoff` | MAF | **handoff** / triage | **control transfer** via `handoff_to_*` tools | ✓ | ✓ |
| 05 | `maf_group_chat` | MAF | **group chat** with a manager | **shared blackboard** (whole transcript) | ✓ | ✓ |
| 06 | `maf_agent_as_tool` | MAF | **supervisor** / hierarchical | **encapsulated function call** (task in, answer out) | ✓ | ✓ |
| 07 | `maf_workflow_graph` | MAF | explicit **graph** with conditional edges | **typed messages** along edges | ✓ | ✓ |
| 08 | `maf_a2a` | MAF + A2A | **remote** agent as a participant | **network protocol** (A2A 1.0: card + JSON-RPC) | ✓ | - |
| 09 | `langchain_agent` | LangChain | single agent + **middleware** | state dict in/out; **checkpointer** memory | ✓ | n/a |
| 10 | `langgraph_supervisor` | LangGraph | **LLM supervisor** routing over a graph | **shared graph state**, checkpointed per step | ✓ | n/a |
| 11 | `langgraph_human_in_the_loop` | LangGraph | **approval gate** | **pause / resume** through a checkpoint | ✓ | n/a |
| 12 | `foundry_hosted_maf/` | MAF + Foundry | **hosted** agent service | **Responses protocol** over HTTP | ✓ | ✓ |
| 13 | `foundry_hosted_langgraph/` | LangGraph + Foundry | hosted agent service | Responses protocol over HTTP | ✓ | n/a |
| 14 | `call_hosted_agent` | OpenAI SDK | client | `responses.create` + `previous_response_id` | ✓ | - |
| 15 | `openai_agents_sdk` | OpenAI Agents SDK | handoff + agents-as-tools + **guardrail** | control transfer / encapsulated call; guardrail beside the agent | ✓ | n/a |
| 16 | `claude_agent_sdk` | Claude Agent SDK | **vendor harness**: built-in tools, sub-agent, hooks | in-process **MCP** tools; delegation via the `Agent` tool | ✓\* | n/a |
| 17 | `github_copilot_sdk` | GitHub Copilot SDK | **vendor harness**, bring-your-own-model | session **event stream**; hooks + permission callbacks | ✓ | ✓ |

*n/a*: no .NET SDK exists (LangChain, OpenAI Agents SDK, Claude Agent SDK).
*-*: not written yet (C# A2A is preview-only; the Python client 14 already calls
the C# hosted agent 12). *\**: needs a signed-in Claude Code; without `--live`
it explains itself and exits, so the offline smoke test still passes.

### The one comparison to teach

How much of the conversation does each agent see? The mock server prints it
(`N msgs in context`), so this is visible live, offline:

| Pattern | What the next agent receives |
|---|---|
| sequential (02) | **everything** so far - grows every hop |
| concurrent (03) | only the original input - agents never see each other |
| handoff (04) | the conversation, **cleaned** of routing tool calls |
| group chat (05) | **everything** - that is the point, and the cost |
| agent-as-tool (06) | **one task string** - total isolation |
| A2A (08) | **one message** - your transcript stays on your side |
| hosted (12-14) | the platform's stored history, addressed by `previous_response_id` |

## Frameworks versus vendor harnesses (samples 15-17)

Samples 01-13 use **frameworks**: you compose the agent from a model, tools and
an orchestration. The vendors' own SDKs are something else - a finished
**harness** (loop, built-in tools, permissions, context management) that you
configure. Anthropic's own framing works for all of them: *who supplies the
harness, and who supplies the deployment?*

| Vendor | Harness you can embed | Hosted (they run it) | Runs on the course endpoint? |
|---|---|---|---|
| Microsoft | MAF (a framework - you build the harness) | Foundry hosted agents (12-13) | yes |
| OpenAI | Agents SDK (15) - small; sandboxed file/shell harness in Python | Responses API hosted tools; Codex cloud | **yes** (any Chat Completions endpoint) |
| Anthropic | Claude Agent SDK (16) - Claude Code as a library | Managed Agents (loop + per-session sandbox) | no - Claude only |
| GitHub | Copilot SDK (17) - Copilot CLI as a library | Copilot coding agent (issue -> PR) | **yes**, via `provider` (bring your own model) |

The same two guardrails appear in both harness SDKs, under the same names: a
**pre-tool-use hook** (sees and can veto every call) and a **permission
handler** (answers "may this tool do this?"). Allow-list tools, confine paths,
refuse by default when nobody is watching.

## Run

```bash
uv run tools/mock_server.py                                        # terminal 1
uv run  samples/03-agents/python/05_maf_group_chat.py --profile mock
dotnet run samples/03-agents/csharp/05_maf_group_chat.cs -- --profile mock
```

Hosted agents are servers; start one, then call it:

```bash
uv run samples/03-agents/python/12_foundry_hosted_maf/main.py --profile mock      # or 13_..., or:
dotnet run --project samples/03-agents/csharp/12_foundry_hosted_maf
uv run samples/03-agents/python/14_call_hosted_agent.py                              # terminal 3
```

Deploying to Foundry: [python/12_foundry_hosted_maf/README.md](python/12_foundry_hosted_maf/README.md).

Everything at once: `uv run tools/smoke_test.py`.

## Traps found while building this (all verified on the pinned versions)

These are why every snippet was run before it was written down. Most samples
on the web predate at least half of them.

**Microsoft Agent Framework - Python 1.19**
1. `OpenAIChatClient` is the **Responses** API client. The Chat Completions one
   (what Ollama, LM Studio and every gateway speak) is `OpenAIChatCompletionClient`.
2. A **built workflow is stateful**: reuse one and the next run inherits the
   previous run's messages (measured 3 -> 6 -> 8). Build one per conversation.
3. Handoff participants **must** set `require_per_service_call_history_persistence=True`;
   the builder refuses otherwise.
4. Handoff always ends with a `request_info` event asking the user - it is
   conversational by design, even in autonomous mode.
5. Group chat hides participant turns unless `intermediate_output_from="all"`,
   and then they arrive as `intermediate`, not `output`, events.
6. One `asyncio.run` per script: the agent's async HTTP client is bound to the
   first event loop; a second `asyncio.run` fails with "Event loop is closed".
   Same cause, different face in A2A: a server thread needs its own client.
7. `agent-framework-a2a`'s own docstring example is stale (`OpenAIResponsesClient().as_agent`
   no longer exists). a2a-sdk 1.x replaced `a2a.server.apps` with `a2a.server.routes`.

**Microsoft Agent Framework - .NET 1.22**
8. `AgentResponseUpdateEvent` **derives from** `WorkflowOutputEvent`. Test for the
   update type first, or the first streamed token is taken as the final output
   and the loop exits with the workflow still running.
9. `AIFunctionFactory.Create(LocalFunction)` in a top-level program names the
   tool `_Main_g_LocalFunction_0_0`. Pass `name:`.
10. Handoff functions are numbered (`handoff_to_1`), so the target's
    `Description` is the only routing signal. Each user turn restarts at the
    start agent (Python stays with the current owner).
11. `GetNewThread` is now `CreateSessionAsync`; `AgentThread` is `AgentSession`.

**Foundry hosted agents**
12. The hosting adapter is `agent-framework-foundry-hosting` (Python) /
    `Microsoft.Agents.AI.Foundry.Hosting` (.NET). `azure-ai-agentserver-agentframework`,
    which most search results still show, stopped shipping in March 2026.
13. Microsoft's LangGraph sample pins `openai<3`; that belongs to
    `azure-ai-projects` 2.4. Version 2.7 **requires** `openai>=3`.
14. `client.responses.stream()` demands a `model`; a hosted agent has none. Use
    `responses.create(stream=True)`.

**LangChain 1.x**
15. `create_agent` replaced `create_react_agent`; legacy chains live in
    `langchain-classic`.

**Vendor harness SDKs**
16. OpenAI Agents SDK 0.22: **tracing is on by default and uploads runs to
    OpenAI** using `OPENAI_API_KEY`, even when the model is Foundry or Ollama.
    `set_tracing_disabled(True)` or plug in your own exporter. Its built-in
    sessions now store history on OpenAI's side (`SQLiteSession` is gone from
    the top level), so carry history with `result.to_input_list()` elsewhere.
17. OpenAI keeps the handoff call in the receiving agent's history (4 messages
    in sample 15); MAF strips it (2 messages in sample 04).
18. Claude Agent SDK: allow-listing *tools* does not confine *paths* - in a live
    run a read-only sub-agent read inside `.venv/site-packages`. Confine paths in
    a `PreToolUse` hook. The delegation tool is `Agent` (older docs: `Task`);
    MCP tools are loaded lazily through `ToolSearch`. A run cost ~$0.50 on
    Opus 5 - set `max_budget_usd`.
19. Copilot SDK 1.0.14: a pre-tool hook returning `permissionDecision: "allow"`
    **silently pre-approves the call** - the permission handler is never asked.
    Audit hooks must return no decision. The SDK runs its own Copilot runtime
    (1.0.85 here), not the `copilot` CLI on PATH (0.0.350 here).
20. Copilot .NET SDK: the permission-decision types are still
    `[Experimental("GHCP001")]` in the GA release, and `ProviderConfig` exists
    in two namespaces.

## Not covered (yet), and why

* **Magentic-One** orchestration (`MagenticBuilder`) - powerful, but hard to
  show honestly offline; a live-model demo, not a lab.
* **Foundry prompt agents** (configuration-only agents in the portal) - a demo
  in the portal is clearer than code.
* **Google ADK 2.0** - one slide in the deck; the patterns above transfer one to one.
* **Anthropic Managed Agents, Copilot coding agent, OpenAI Codex cloud** - the
  hosted halves of 15-17; demos in their own consoles, not labs.
* **DevUI** (`agent-framework-devui`, beta) - worth a live demo of sample 05.
