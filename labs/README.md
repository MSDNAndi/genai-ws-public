# Building Stuff with GenAI — labs

Four hands-on labs for the day, each in **Python**, **C#** (.NET 10 single-file apps) and **TypeScript** (Node 22+,
plain ES modules) — Lab 4 is Python-first. Every lab has a core that everyone finishes and stretch goals for
the fast ones. All labs talk to models through the same OpenAI-compatible client, configured in one file: `labs/.env`.

| | Lab | You build | Core |
|---|---|---|---|
| 0 | [`00-setup`](00-setup/SETUP.md) | a machine that is ready (do this **before** the day) | 45–60 min at home |
| 1 | [`01-hello-model`](01-hello-model/README.md) | calls, knobs, structured output, the tool loop by hand, same code on other models | core + stretch |
| 2 | [`02-rag-mcp`](02-rag-mcp/README.md) | PDF → chunks → embeddings → cited answers → your own MCP server | core + stretch |
| 3 | [`03-agents`](03-agents/README.md) | an agent with MCP tools, a two-agent workflow, a critic, tracing | core + stretch |
| 4 | [`04-local-media`](04-local-media/README.md) | local models measured, ComfyUI from code, one knob at a time, cloud image + speech | core + stretch |

## How every lab folder works
- `python/`, `csharp/`, `typescript/` hold **starters**: complete, runnable files, except for a few blocks marked
  `TODO n` that you write. `solution/` next to them holds the finished version.
- Settings come from `labs/.env` (copy `.env.example`); real environment variables win over the file.
- Keys travel in an `api-key` header (the workshop gateway requires it). Models are deployment names.

## Versions (tested together on 2026-09-22)
Python: openai 3.18 · Microsoft Agent Framework 1.19 (core, openai, orchestrations) · mcp 1.30 · LangChain 1.4 /
LangGraph 1.2 · MarkItDown 0.1.8 (`requirements.txt`). C#: Microsoft.Agents.AI 1.22 · OpenAI 2.13 ·
ModelContextProtocol 2.2 · DotNetEnv 3.2 · OpenTelemetry 1.19 (pinned per file with `#:package`). TypeScript: openai
7.22 · ai 7.0 · @ai-sdk/mcp 2.0 · @modelcontextprotocol/server + client 2.0 · zod 4.6 (`package.json`).

**Verified on:** 2026-09-22 — every solution against a real local model (Ollama 0.34.3 with qwen3.5:2b / qwen3:1.7b and
bge-m3; Linux, CPU only) · 2026-09-23 — all solutions and starters, Python/C#/TypeScript, against the offline mock after
the settings were renamed to `GENAI_*` · **still open:** the workshop endpoint (not provisioned yet), a clean Windows and
macOS laptop following `00-setup/SETUP.md` only, ComfyUI on a real GPU. Update this line after every test run
(`python _tools/test_labs.py`, see `_tools/README.md`).

## When things break on the day
- The endpoint is down or the Wi-Fi is gone: the instructor starts `00-setup/mock/mock_openai_server.py` with
  `MOCK_HOST=0.0.0.0` so the room can reach it; set
  `GENAI_BASE_URL=http://<instructor-ip>:8123/v1`, `GENAI_API_KEY=test`, `GENAI_MODEL=mock-model`. Answers become
  echoes, but every script runs.
- Or work fully local: `GENAI_BASE_URL=http://localhost:11434/v1`, `GENAI_API_KEY=ollama`, `GENAI_MODEL=qwen3.5:4b`,
  `GENAI_REASONING_EFFORT=none`, `GENAI_EMBED_MODEL=bge-m3`.

For instructors and maintainers: `_tools/README.md` (tests, starters, mocks). Edit `*/<language>/solution/*` only and
regenerate the starters with `python _tools/make_starters.py`. A new lab folder in the same shape:
`python ../skills/workshop-lab-authoring/scripts/lab_scaffold.py . 05 <slug> "<Title>" --segment <n>` (from `labs/`).
