# Lab 3 — Two agents and a workflow (core + stretch)

**Verified on:** 2026-09-22 against Ollama 0.34.3 (qwen3.5:2b, qwen3:1.7b, bge-m3 · Linux, CPU only) and 2026-09-23
against the offline mock (all solutions and starters) · not yet against the workshop endpoint (not provisioned).

**Goal:** build an agent with Microsoft Agent Framework (Python and C#) or AI SDK (TypeScript), give it your Lab 2
MCP server as a tool, chain two agents into a workflow, add a critic, and look inside with tracing.

**Before you start:** the Lab 2 index exists (`labs/02-rag-mcp/build/index.json` — run Lab 2 step 2 in any language).
The agents always start the *finished* Lab 2 server, so an unfinished Lab 2 starter does not block you.

| Step | Python (MAF 1.19) | C# (MAF 1.22) | TypeScript (AI SDK 7) |
|---|---|---|---|
| 1 agent + tools + memory | `01_agent.py` | `01_agent.cs` | `01_agent.mjs` |
| 2 agent + MCP tools | `02_agent_with_mcp.py` | `02_agent_with_mcp.cs` | `02_agent_with_mcp.mjs` |
| 3 researcher → writer | `03_workflow.py` · TODO 1 | `03_workflow.cs` · TODO 1 | `03_workflow.mjs` · TODO 1 |
| 4 + critic | `04_critic.py` · TODO 2 | `04_critic.cs` · TODO 2 | `04_critic.mjs` · TODO 2 |
| 5 tracing | `05_tracing.py` · TODO 3 | `05_tracing.cs` · TODO 3 | — |
| stretch | `06_langgraph.py`, `07_devui.py` | | |

## Steps
**1 · An agent is a loop with a runtime — `01_agent`.** Two tools, instructions, and a *session* (the memory).
Three questions in one session — "And what is that in Fahrenheit?" only works because the session remembers Mannheim.
The last call runs without the session: same agent, no memory.

**2 · Tools over MCP — `02_agent_with_mcp`.** No adapter code: the MCP server's tools become the agent's tools
(`MCPStdioTool` in Python, `McpClient` + `ListToolsAsync()` in C#, `createMCPClient` in TypeScript).
*Checkpoint:* the night-flight answer cites the handbook. Is it *right*? (Max 90 m at night.) Small models sometimes
say "yes" and then quote the limit that contradicts them — tools make answers groundable, not automatically correct.

**3 · Two agents, one workflow — `03_workflow` · TODO 1.** Write the two job descriptions: a researcher that only
collects cited facts with the tool, a writer that turns them into an 80-word customer reply.
Python/C#: a *sequential* workflow (`SequentialBuilder` / `AgentWorkflowBuilder.BuildSequential`) passes the growing
conversation along. TypeScript: AI SDK has no workflow builder, so you chain the agents in code.
*A real-world gotcha:* how does the researcher's output reach the writer? Python MAF 1.19 passes it on as an
**assistant** message; frontier models cope, but small local models often think they already answered and return an
**empty** reply. `handoffs_as_user()` in `lab3_common.py` re-labels other agents' turns as user turns (10 lines — read
it). C# MAF 1.22 already hands the previous agent's reply over as a *user* message (plus its tool calls). Same pattern,
different plumbing — look at the requests with the mock's `MOCK_LOG` (see `_tools/README.md`).

**4 · Add a critic — `04_critic` · TODO 2.** Researcher → writer → critic → writer: a group chat with a *fixed*
speaking order (`next_speaker`), a hard round limit and an early exit when the critic says APPROVED.
*Checkpoint:* two or more drafts, the last one shorter or more correct than the first.
Why not let an LLM pick the next speaker? You can (`orchestrator_agent=`) — but a fixed order is cheaper, testable and
predictable; use LLM routing only when the path really depends on the content.

**5 · Look inside — `05_tracing` · TODO 3.** Switch on OpenTelemetry with a tiny one-line-per-span exporter:
`invoke_agent` → `chat` → `execute_tool` → `chat`, with token counts and tool arguments. The same spans go to
Application Insights, Aspire or Langfuse by setting `OTEL_EXPORTER_OTLP_ENDPOINT` — no code change.

## Stretch
- **Another brain, same agent.** Set `GENAI_MODEL` to your `GENAI_MODEL_2` (DeepSeek, Grok, Kimi …) or point
  `GENAI_BASE_URL` at Ollama and re-run step 2. Which models call the tool, which guess?
- **`06_langgraph.py`** — the same idea as an explicit graph: a checkpointer keeps state per `thread_id`, and a human
  approval step (`interrupt()` / `Command(resume=…)`) pauses the graph until you answer.
- **`07_devui.py`** — `pip install -r ../requirements-extras.txt`, then chat with your agent and workflow in the
  browser and inspect each step.
- **Danger zone:** give an agent a tool that *changes* something (writes a file, sends mail) and require approval first
  (`MCPStdioTool(..., approval_mode="always_require")` in Python). Discuss: which tools must never run unapproved?

## Fallback
- **No workshop key, or the endpoint is down:** Ollama with `qwen3.5:4b` and `GENAI_REASONING_EFFORT=none` runs every step;
  small models are slower in multi-agent steps and sometimes reply with an empty message after a hand-off (the Python
  code already works around it).
- **No Wi-Fi:** the instructor's mock (see Lab 1): the agents, tools, workflows and traces all run; the answers are echoes.
- **Tracing (step 5) needs no cloud:** the spans are printed in your terminal; a trace backend is optional.

## Troubleshooting
"Lab 2 index is missing" → Lab 2 step 2 · empty writer reply → see step 3 · the run stops at the round limit → your
model never says APPROVED (fine; the limit exists for exactly this) · tracing prints nothing → the exporter batches:
the script flushes at the end, keep that line · C#: the first run builds the Lab 2 server, give it ~20 s.

## Why it matters
An agent is the Lab 1 loop plus a runtime that owns memory, tools, budgets and permissions. Teams of agents are
mostly *plumbing between transcripts* — roles, hand-offs, stop conditions — and that plumbing is where they break.
