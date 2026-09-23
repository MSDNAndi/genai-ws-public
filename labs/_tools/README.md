# _tools — for instructors and maintainers

| Tool | What it does |
|---|---|
| `make_starters.py` | generates every starter from `*/*/solution/*` by replacing the `>>> TODO … <<< TODO` blocks with a hint and a placeholder that fails loudly. Edit **solutions only**, then run it. `--check` exits 1 if a starter is stale. |
| `test_labs.py` | runs every solution (or `--starters`) against the endpoint in `labs/.env` / the environment; `--lab 02 --lang csharp` to narrow; logs in `_tools/test_logs/`. Skips servers and UIs (`*_server*`, `devui`). |
| `comfy_mock.py` | a stand-in for ComfyUI's HTTP API (`/prompt`, `/history`, `/view`) that renders the knobs into a flat image — tests Lab 4 without a GPU. `test_labs.py` drives it with `04-local-media/comfyui_workflows/01_txt2img_sdxl.json` (falls back to the minimal `fixtures/txt2img_api.json`). |
| `../00-setup/mock/mock_openai_server.py` | the OpenAI-compatible offline mock (chat + SSE, tools, structured output, Responses + SSE, hashed bag-of-words embeddings, images, speech; `MOCK_REQUIRE_API_KEY` emulates the gateway's 401; `MOCK_LOG=file.jsonl` records every request body — handy to *show* what a framework really sends; `MOCK_HOST=0.0.0.0` serves the room). |

## Before the day
1. `python _tools/make_starters.py --check`
2. Against the real workshop endpoint (a spare key): `python _tools/test_labs.py` (all languages), then
   `python _tools/test_labs.py --starters`.
3. Against Ollama with the attendee default model (the offline path): same two commands with the local `.env` values.
4. Re-run `labs/_verified_snippets/run_all.sh --real` if any package version changed.

## Known model behaviours worth showing (seen with small local models, 2026-09-22)
- Lab 1 step 4: two tools requested in parallel, the second with a *guessed* argument.
- Lab 2 step 3: "K-4 payload in rain" answered with the dry value — the PDF table lost its columns (`07_tables.py` fixes it).
- Lab 3 step 3 (Python): an empty writer reply when the hand-off arrives as an assistant message — `handoffs_as_user()`;
  C# MAF sends the previous agent's reply as a user message and is not affected.
- Thinking models on a CPU: 40 s instead of 5 s for the same one-liner until reasoning is switched off.
