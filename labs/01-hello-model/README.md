# Lab 1 — Hello, model (core + stretch)

**Verified on:** 2026-09-22 against Ollama 0.34.3 (qwen3.5:2b, qwen3:1.7b, bge-m3 · Linux, CPU only) and 2026-09-23
against the offline mock (all solutions and starters) · not yet against the workshop endpoint (not provisioned).

**Goal:** call a model from code, feel the knobs, get typed output, and write the tool-call loop that every agent is
built on — then run the *same* code against a different vendor and against your laptop.

You will see: one OpenAI-compatible client for everything · sampling knobs vs reasoning effort · JSON Schema as a
contract · the loop `model → tool call → your code → tool result → model`.

**Before you start:** `00-setup` is green and `labs/.env` holds the values from your handout card.

## How this folder works
Each language folder has *starters* (with `TODO` blocks to fill in) and a `solution/` folder with the finished code.
Files without a TODO simply run — read them, run them, change them.

| | Python | C# | TypeScript |
|---|---|---|---|
| run a step | `cd python` · `python 01_hello.py` | `cd csharp` · `dotnet run --file 01_hello.cs` | `cd typescript` · `node 01_hello.mjs` |
| peek at the answer | `python solution/04_tool_loop.py` | `dotnet run --file solution/04_tool_loop.cs` | `node solution/04_tool_loop.mjs` |

## Steps
**1 · First call — `01_hello`.** Run it. Then change the system prompt and run again; print the raw response
(the comments show how) and find the token usage and the `finish_reason`.
*Checkpoint:* an answer plus a usage line.
*Watch for:* a small local model (qwen3.5:2b in testing) explains *API* or *crypto* tokens — the question never says
"LLM". Put the domain into the system prompt and run again: context fixes more than a bigger model.

**2 · Knobs — `02_knobs`.** Same prompt at temperature 0, 1 and 1.6, then `top_p` and `seed`.
With `gpt-5-mini` you will get an error instead: reasoning models fix temperature and offer `reasoning_effort` —
the script shows both. Run it again with `GENAI_MODEL=<your GENAI_MODEL_2>` (a non-reasoning vendor) to see the
temperature effect. *What to notice:* temperature 0 ≈ repeatable, not guaranteed; reasoning tokens are billed but hidden.

**3 · Structured output — `03_structured` · TODO 1.** Describe the `Session` shape (Pydantic / C# record / Zod) and let
the SDK turn it into a JSON Schema. *Checkpoint:* a typed object, total minutes computed from it.
*Try:* the `start` field says "HH:MM" in its description — did your model obey? Descriptions are hints; add a
`pattern` (or an enum) when it matters.

**4 · The tool loop, by hand — `04_tool_loop` · TODO 2.** Append the assistant turn, run each requested tool, send the
results back as `tool` messages, repeat until the model answers. *Checkpoint:* the answer mentions 19 °C and °F.
*Watch for:* some models request `get_weather` **and** `to_fahrenheit` in the same turn — they guessed the temperature
before knowing it (parallel calls cannot use each other's results). Try `parallel_tool_calls=False`.

**5 · Same code, other models — `05_same_code_other_model`.** One prompt and one tool round-trip against the workshop
model, a second vendor behind the same key (`GENAI_MODEL_2`), and Ollama (+ LM Studio) if running.
*Checkpoint:* at least two targets answer. Compare latency, length and tool-calling habits — this is the thesis of the day.

## Stretch
- `06_responses_api` — the newer Responses API (`input`, `previous_response_id`, semantic streaming events). Foundry,
  OpenAI and Ollama (0.34) speak it; some gateways and servers only speak Chat Completions.
- TypeScript only: `07_ai_sdk_agent.mjs` — the step 4 loop, run for you by AI SDK 7's `ToolLoopAgent`.
- Point `.env` at Ollama (see `00-setup/SETUP.md` step 6) and run steps 1–4 fully offline.

## Fallback
- **No workshop key yet, or the endpoint is down:** point `labs/.env` at Ollama — `GENAI_BASE_URL=http://localhost:11434/v1`,
  `GENAI_API_KEY=ollama`, `GENAI_MODEL=qwen3.5:4b`, `GENAI_REASONING_EFFORT=none`. Every step runs unchanged.
- **No Wi-Fi at all:** the instructor's mock (`GENAI_BASE_URL=http://<instructor-ip>:8123/v1`, `GENAI_API_KEY=test`,
  `GENAI_MODEL=mock-model`). Answers are echoes, but the tool loop and structured output really run.
- **Step 5 needs two targets:** Ollama + the workshop endpoint, or Ollama + the mock.

## Troubleshooting
401 → key/header · 404 → model name or URL (`…/openai/v1`) · 429 → per-minute limit, wait a minute · 403 → today's quota is used up, ask the instructor ·
"reasoning_effort not supported" → remove `GENAI_REASONING_EFFORT` for that model · a local model "thinks" for a long
time → `OLLAMA_REASONING_EFFORT=none`.

## Why it matters
Every product you will meet today — RAG, MCP servers, agents, media pipelines — is this loop plus context. Once the
client is an OpenAI-compatible `base_url`, the vendor is a configuration value, not an architecture decision.
