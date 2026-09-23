# Lab 2 — RAG + MCP (core + stretch)

**Verified on:** 2026-09-22 against Ollama 0.34.3 (qwen3.5:2b, qwen3:1.7b, bge-m3 · Linux, CPU only) and 2026-09-23
against the offline mock (all solutions and starters) · not yet against the workshop endpoint (not provisioned).

**Goal:** turn three PDFs into a searchable index, answer questions *with citations* (and admit when the documents
don't say), then publish your search as an **MCP server** that any agent or AI app can use.

The documents are about *Kestrel Drone Logistics*, a fictional company — the model cannot know the answers without
retrieval, so you can see whether RAG works. They live in `data/` (`make_pdfs.py` regenerates them).

| Step | Python | C# | TypeScript |
|---|---|---|---|
| 1 ingest PDF → chunks | `01_ingest.py` | — (uses `data/prebuilt/chunks.jsonl`) | — (same) |
| 2 embed → `build/index.json` | `02_embed.py` | `02_embed.cs` | `02_embed.mjs` |
| 3 ask with citations | `03_ask.py` · TODO 2 | `03_ask.cs` · TODO 2 | `03_ask.mjs` · TODO 2 |
| 4 MCP server | `04_mcp_server.py` · TODO 3 | `04_mcp_server.cs` · TODO 3 | `04_mcp_server.mjs` · TODO 3 |
| 5 MCP client | `05_mcp_client.py` | `05_mcp_client.cs` | `05_mcp_client.mjs` |
| stretch: evaluate | `06_eval.py` | `06_eval.cs` | — |
| stretch: fix tables | `07_tables.py` | — | — |

All languages read and write the same `build/index.json`, so a Python index works with the C# server and vice versa.

## Steps
**1 · Ingest (Python) — `01_ingest.py` · TODO 1.** MarkItDown extracts the text; you pack paragraphs into ~700-character
chunks with a one-paragraph overlap. Open `build/kestrel_operations_handbook.md` and look at the fleet **table**.
C#/TypeScript: skip — `data/prebuilt/chunks.jsonl` is the output of this step.

**2 · Embed — `02_embed`.** One `/embeddings` call per 32 chunks; vectors are normalised and saved with the chunks in
`build/index.json` — the simplest possible vector store. To embed locally while chatting in the cloud, set
`EMBED_BASE_URL=http://localhost:11434/v1`, `EMBED_API_KEY=ollama` and `GENAI_EMBED_MODEL=bge-m3`.

**3 · Ask — `03_ask` · TODO 2.** Retrieve the top 4 chunks, number them, and write the grounding instructions: answer only
from the sources, cite them like `[2]`, otherwise say "Not in the documents". *Checkpoint:* the firmware question is
answered with a citation and "Who is the CEO?" is refused.
*Now look closely at the K-4 payload in rain.* Many runs answer **2.5 kg** — the dry value. Retrieval found the right
chunk; the PDF-to-text step scrambled the table columns. That is the most common RAG failure in real projects
(stretch: `07_tables.py`).

**4 · MCP server — `04_mcp_server` · TODO 3.** Register `search_docs(query, k)`; its docstring/description is what the
model reads when it decides to call it. The server also exposes each document as a resource
(`kestrel://docs/<name>`) and — in Python — a prompt template. Never print to stdout in a stdio server: stdout *is*
the protocol.

**5 · Use it from code — `05_mcp_client`.** Starts your server as a child process, lists tools, calls `search_docs`,
reads a resource. *Checkpoint:* two hits for "night flight altitude limit".
Gotcha you will meet everywhere: stdio clients start servers with a minimal environment — our servers find
`labs/.env` themselves; MCP hosts have an `env` field for the same reason.

**6 · Use it from an AI app.** Plug the *same* server into a host you use (absolute paths; use the Python from
your `.venv`, not the system one):

| Host | How (as of 2026-09 — check your host's docs if a field was renamed) |
|---|---|
| MCP Inspector | `npx @modelcontextprotocol/inspector <labs>/.venv/bin/python <labs>/02-rag-mcp/python/solution/04_mcp_server.py` |
| Claude Code | `claude mcp add kestrel-docs -- <labs>/.venv/bin/python <labs>/02-rag-mcp/python/solution/04_mcp_server.py` |
| VS Code + GitHub Copilot (agent mode) | `.vscode/mcp.json`: `{"servers": {"kestrel-docs": {"type": "stdio", "command": "<python>", "args": ["<…>/04_mcp_server.py"]}}}` |
| LM Studio | Program → Install → Edit `mcp.json`: `{"mcpServers": {"kestrel-docs": {"command": "<python>", "args": ["<…>/04_mcp_server.py"]}}}` |

C# server: run `dotnet build 04_mcp_server.cs` once, then use command `dotnet` with args
`["run", "--file", "<…>/04_mcp_server.cs", "--no-build"]` (build output on stdout would break the protocol).
TypeScript server: command `node`, args `["<…>/04_mcp_server.mjs"]`.
Then ask the host: *"Using kestrel-docs: how long are proof-of-delivery photos kept?"*

## Stretch
- **Measure — `06_eval`.** Six golden questions; retrieval hit@4 and answer correctness. Change `CHUNK_CHARS` in step 1
  (300 / 1500), re-run steps 1, 2 and the eval. Measure before you tune.
- **Fix the table — `07_tables.py`.** Read tables cell by cell (pdfplumber), add each row as a self-contained sentence,
  re-run `02_embed.py` and `06_eval.py`. Structure-aware extraction is what Docling and Azure Content Understanding
  sell.
- **Write a skill.** A `SKILL.md` that tells an agent *when* and *how* to use kestrel-docs (cite chunk ids, refuse
  when nothing is found). Tools are capabilities; skills are know-how.

## Fallback
- **PDF extraction fails to install or run (step 1):** skip it — `02_embed` uses `data/prebuilt/chunks.jsonl`, the
  output of step 1, in every language.
- **No embedding model on your endpoint, or offline:** embed locally with Ollama — `EMBED_BASE_URL=http://localhost:11434/v1`,
  `EMBED_API_KEY=ollama`, `GENAI_EMBED_MODEL=bge-m3`. Query with the same model you indexed with.
- **No MCP host installed (step 6):** `05_mcp_client` and the MCP Inspector (`npx @modelcontextprotocol/inspector …`) show
  the same server.
- **No Wi-Fi:** the instructor's mock (see Lab 1). Its embeddings are hashed word counts, so retrieval matches on
  shared words only, and the answers are echoes — enough to build and test the MCP server.

## Troubleshooting
`index.json not found` → run steps 1–2 (or 2 only for C#/TS) · the index was built with a different embedding
model than you query with → re-run step 2 · the MCP host shows no tools → absolute paths, the right Python, check the
host's MCP log · "Connection closed" from the client → the server crashed at start: run it directly to see the error.

## Why it matters
The context window is the product: what you retrieve, how you cut it and how you cite it decides the answer more than
the model does. MCP turns that retrieval into a component every agent and AI app can plug in — Lab 3 does exactly that.
