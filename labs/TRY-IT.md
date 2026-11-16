# Try it yourself: every demo from the talk

**Fastest: open [TRY-IT.ipynb](TRY-IT.ipynb) and click ▶ next to your slide — no copy-paste.** Or Ctrl+Shift+P → *Tasks: Run Task* → pick the slide.

Every "LIVE DEMO" slide has a version you can run in your codespace. Run the commands **from `labs/`** (the terminal starts there). Where a demo needs a GPU or software a codespace cannot have, you get the closest cloud version or a clear "watch only".

No setup needed: same key, same settings as the labs. Tip: open any `.py`, `.cs` or `.mjs` file and click **▶ Run Code** (top right).

- [Segment 1 · Foundations](#segment-1)
- [Segment 2 · Integrating AI](#segment-2)
- [Segment 3 · Agents](#segment-3)
- [Segment 4 · Local AI and media](#segment-4)


---
<a id="segment-1"></a>

# Segment 1 — try the live demos yourself

Each block runs in your Codespace terminal **from `labs/`** (`cd /workspaces/genai-ws-public/labs` if you are elsewhere).
Your key comes from the Codespace secret or `labs/.env`, exactly like the labs. Nothing here changes any file.

## S1 · Demo: tokens and attention, live (slide 20)

Try it:

```bash
python try/s1_tokens.py
python try/s1_tokens.py "Donaudampfschifffahrt ist schön 🚢"
```

Then open the two browser tools (any browser works, your Codespace's too):
<https://tiktokenizer.vercel.app> (pick `o200k_base`) and <https://poloclub.github.io/transformer-explainer>
(type "the cat sat on the", click one attention head, drag the temperature slider).

What to notice:
- `" strawberry"` is a single token, not ten letters — that is why letter counting trips models up.
- The German compound costs more tokens than the English sentence; an emoji can be several tokens (shown as `<raw bytes>`).
- The script and tiktokenizer give the same ids for `o200k_base`: tokenizing is plain code, not magic.

## S1 · Demo: what reasoning_effort costs — and who refuses it (slide 51)

Try it:

```bash
GENAI_MODEL=gpt-5-nano python try/s1_effort_cost.py
GENAI_MODEL=DeepSeek-V4.1-Flash-1017 python try/s1_effort_cost.py
```

What to notice:
- gpt-5-nano refuses `temperature=0.2` with a 400: reasoning models lock sampling knobs and offer `reasoning_effort` instead.
- low → medium → high: same answer, but hidden reasoning tokens grow (test run: 0 → 192 → 384) and so does the estimated bill; hidden tokens are billed as output.
- DeepSeek accepts temperature; the workshop gateway drops `reasoning_effort` for models that would reject it (DeepSeek, grok, Llama, gpt-4o-mini), so hidden stays 0. To *see* a refusal, use gpt-5-nano with temperature as above.

The longer lab version (temperature, top_p, seed, then minimal/low/high): `GENAI_MODEL=gpt-5-nano python 01-hello-model/python/solution/02_knobs.py`

Instructor-only part: the APIM response headers with tokens consumed/remaining per key (llm-token-limit policy) — the gateway side of the bill.

## S1 · Demo: one script, five providers (slide 61)

Try it:

```bash
python try/s1_five_providers.py
```

What to notice:
- One client, one URL, one key — five vendors (OpenAI, DeepSeek, xAI, Meta, OpenAI open-weight); only the model name changes.
- Compare seconds and tokens: the "fast-non-reasoning" and Flash models answer in under a second; gpt-5-nano spends extra (hidden) tokens.
- Same question, different style and length. Pick your own list: `python try/s1_five_providers.py gpt-5-nano gpt-oss-120b`.

With tool calling too (workshop model + `GENAI_MODEL_2`): `python 01-hello-model/python/solution/05_same_code_other_model.py`

Instructor-only part: the local Ollama target (gemma4:e4b, no key, no network) — a Codespace has no Ollama; run it on your own laptop.

---
<a id="segment-2"></a>

# Segment 2: try the live demos yourself

Every "LIVE DEMO" slide in Segment 2, as something you can run in your codespace. Open a terminal (it starts in
`labs/`), copy one block, paste, press Enter. Your key and model come from the codespace secret or `labs/.env`,
exactly like the labs. All four use the Lab 2 code and the same three Kestrel PDFs.

---

## S2 · Docling → embeddings → pgvector → a cited answer (slide 79)

Try it:
```bash
bash try/s2_structured_rag.sh
```
What to notice:
- Part 1 prints the fleet table as plain text extraction sees it: the numbers have lost their columns. Which one is "rain"?
  (The model sometimes still guesses 1.8 kg right; look at the source it cites: a flattened chunk.)
- Part 2 adds every table row as one sentence (`K-4 Kestrel: Max payload (rain) = 1.8 kg; ...`): the top hits are now the
  table rows, with much higher scores. The parser, not the model, decides whether the question is answerable.
- "Who is the CEO?" → *Not in the documents.* both times.

Instructor-only part: Docling and pgvector (Docker) run on the instructor laptop; your version uses pdfplumber
(Lab 2 `07_tables.py`) and the in-memory vector store. Docling pulls in PyTorch (several GB), so it is not in the codespace.

---

## S2 · Prompt injection, live (slide 89)

Try it:
```bash
python try/s2_prompt_injection.py; python try/s2_prompt_injection.py --guard
```
What to notice:
- One extra "policy update" chunk is retrieved first, and the answer obeys its hidden sentence ("Photos are deleted
  immediately ... code FREEBIRD") instead of the real policy (30 days). The order came in as *data*.
- With `--guard` the chunk is screened out and sources are wrapped as untrusted data: the answer is "30 days [1]".
- The guard is a regex: rephrase the hidden sentence in `POISON` and run again. That gap is why production uses a trained
  classifier (Prompt Shields) plus a tool allow-list.

Instructor-only part: the poisoned PDF with white text, re-indexed through the full pipeline.

---

## S2 · One MCP server in Inspector, LM Studio and Claude Code (slide 97)

Try it (host 1, MCP Inspector, in the terminal; the first line builds the Lab 2 index once):
```bash
test -f 02-rag-mcp/build/index.json || python 02-rag-mcp/python/solution/02_embed.py
npx -y @modelcontextprotocol/inspector --cli --connect-timeout 60000 -e GENAI_API_KEY=$GENAI_API_KEY .venv/bin/python 02-rag-mcp/python/solution/04_mcp_server.py --method tools/call --tool-name search_docs --tool-arg "query=how long are proof-of-delivery photos kept?" --tool-arg k=2
```
Host 2, **GitHub Copilot Chat**: the same server is already registered in `.vscode/mcp.json` at the repo root.
Open Copilot Chat → mode **Agent** → tools icon → tick `kestrel-docs` (start it if VS Code asks) → ask
*"Using kestrel-docs: how long are proof-of-delivery photos kept?"*
What to notice:
- Same command in both hosts, zero code changes: only the host's config format differs.
- The Inspector shows the raw tool result the model sees (chunk id, score, text): "kept for 30 days".
- The gotchas: absolute paths (`${workspaceFolder}`), the venv's Python, nothing on stdout, and stdio servers start with a
  minimal environment (that is why the key is passed with `-e` / `env`). Drop `--cli ...` after the script path for the
  browser UI. Own machine with the key only in `labs/.env`? Remove the `env` line from `.vscode/mcp.json`.

Instructor-only part: LM Studio with a local model and Claude Code (`claude mcp add` + `/mcp`).

---

## S2 · One SKILL.md, three agents (slide 99)

Try it: the skill is `.github/skills/kestrel-support/SKILL.md` (repo root), the folder VS Code Copilot scans for
project skills. Build the index first (first line of the slide 97 block), then in **Copilot Chat → Agent** ask:
```text
/kestrel-support A Standard delivery arrived 41 minutes late. What does the customer get?
```
(Or just ask a Kestrel question without the slash: Copilot loads a skill when the request matches its description.)
What to notice:
- The skill is know-how, the MCP server is the capability: the skill tells the agent to call `search_docs`, cite chunk
  ids and say *Not in the documents.* when nothing matches. Try "Who is the CEO of Kestrel?".
- If your Copilot does not list the skill under `/`, paste the body of the SKILL.md into the chat before your question:
  same effect, by hand.

Instructor-only part: Copilot CLI, Claude Code and Goose picking up the same file side by side.

---
<a id="segment-3"></a>

# Segment 3: try the live demos yourself

Every "LIVE DEMO" slide in Segment 3, as something you can run in your codespace. Open a terminal (it starts in
`labs/`), copy one block, paste, press Enter. Your key and model come from the codespace secret or `labs/.env`,
exactly like the labs.

The first line of most blocks builds the Lab 2 search index if you skipped Lab 2 (takes a few seconds, once).

---

## S3 · Copilot CLI and Claude Code doing the same task (slide 125)

Try it: use **GitHub Copilot Chat in agent mode** in your codespace. It already knows the Lab 2 MCP server from
Segment 2 (`kestrel-docs`, registered in `.vscode/mcp.json` at the repo root), and the Segment 2 SKILL.md is in the repo.
```text
1. Open Copilot Chat (chat icon in the top bar) -> switch the mode to "Agent"
2. Tools icon -> make sure "kestrel-docs" / search_docs is ticked (start the server if VS Code asks)
3. Ask:  Can I fly a K-2 Sparrow at night at 100 m?
```
What to notice:
- The agent plans first, asks before it runs `search_docs`, and answers with chunk ids.
- The right answer is **no**: the handbook limits night flights to 90 m. If it says yes without searching, ask it to search.
- Same MCP server you built in Lab 2, zero code changes: only the "harness" around it is different.

Optional, the terminal agent: `npx -y @github/copilot` starts GitHub Copilot CLI without installing anything
(it asks you to `/login` with your GitHub account, and needs a Copilot plan). Add the server there with `/mcp`.

Instructor-only part: Claude Code side by side with Copilot CLI runs on the instructor laptop.

---

## S3 · MAF researcher -> writer with the Lab 2 MCP tool (slide 137)

Try it (Python, then the C# twin):
```bash
test -f 02-rag-mcp/build/index.json || python 02-rag-mcp/python/solution/02_embed.py
python 03-agents/python/solution/03_workflow.py
dotnet run --file 03-agents/csharp/solution/03_workflow.cs
```
What to notice:
- RESEARCHER NOTES: the researcher calls `search_docs` over MCP and cites chunk ids like `(kestrel_customer_service_policy#0)`.
- WRITER: the writer has no tool; it only sees the researcher's notes. The C# version gives the same shape of answer.
- Optional: `python 03-agents/python/solution/07_devui.py` opens DevUI on port 8090: run the workflow and click through each step.

---

## S3 · The same task in LangGraph (slide 139)

Try it:
```bash
test -f 02-rag-mcp/build/index.json || python 02-rag-mcp/python/solution/02_embed.py
python 03-agents/python/solution/06_langgraph.py
```
At the prompt `'approve' or type feedback >`, type some feedback first, for example `mention the limit in Wh`,
then type `approve`. (`--auto` approves on its own.)

What to notice:
- The graph stops at `human_review`: it pauses the whole run and waits for you.
- Feedback loops back to `write`; `approve` goes to END.
- The last line counts the checkpoints saved for thread `customer-4711`: that saved state is what lets it resume.

---

## S3 · The A2A Bazaar: your agents, one question (slide 141)

Try it: this one is already a lab. Follow the three steps in `03-agents/a2a/README.md` ("Attendees: three commands"):
```bash
cd 03-agents/a2a && python a2a_agent.py --persona pirate
```
Then make port 8100 public (Ports tab -> right-click 8100 -> Port Visibility -> Public) and, in a second terminal,
call a neighbour: `python a2a_call.py https://<neighbour>-8100.app.github.dev "What should we do tonight?"`

What to notice:
- A2A is an agent card plus one JSON-RPC message: MCP is agent-to-tool, A2A is agent-to-agent.
- Your agent logs one line per call, so you see your neighbours' questions arrive.
- No authentication: stop the agent (Ctrl+C) and set the port back to Private when you are done.

Instructor-only part: `bazaar.py` (asking the whole room) runs on the instructor laptop.

---

## S3 · Deploy the workflow as a Foundry hosted agent (slide 145)

Instructor-only part: the whole demo. It needs an Azure subscription, Entra sign-in and `azd`, and Agent Service
endpoints do not accept the workshop key.

What to look at instead (read, no command needed):
- `demos/samples/03-agents/python/12_foundry_hosted_maf/`: `main.py` (the agent), `Dockerfile` and `azure.yaml`
  (how it becomes a container and a hosted agent), `README.md` (the `azd` deploy steps).
- `demos/samples/03-agents/python/14_call_hosted_agent.py`: calling a hosted agent is a normal OpenAI Responses call.
- Notebook version: `demos/notebooks/03-agents/python/12_foundry_hosted_maf/`.

---
<a id="segment-4"></a>

# Segment 4 · try it yourself

The Segment 4 demos run on the instructor laptop (GPU, Ollama, ComfyUI, a microphone). Your codespace has none of
these, so each demo below is either the **honest cloud equivalent** through the workshop gateway, or **Watch only**.
Run every command from `labs/` (`cd labs` in the terminal). Output files land in `labs/out/`: click a `.wav` or `.png`
in the Explorer to play or view it.

## S4 · a Qwen3.8-27B tool call on Ollama (slide 169)

Try it:
```bash
GENAI_MODEL=gpt-oss-120b python 01-hello-model/python/solution/04_tool_loop.py
```
What to notice: the Lab 1 tool loop is unchanged. Only the model changed, and gpt-oss-120b is open weights: you could
host this same model yourself. On your laptop it is the same command with `GENAI_BASE_URL=http://localhost:11434/v1`
and an Ollama model tag. The checkpoint is 19 °C → 66.2 °F after two tool calls.

## S4 · one model, two servers, eight clients (slide 170)

Try it:
```bash
python try/s4_eight_clients.py gpt-oss-120b
```
What to notice: first one client, then eight at the same moment. Each request's tok/s stays about the same, but the
total for all eight is several times higher, because the server batches them. The gateway hides its hardware. Point
`GENAI_BASE_URL` at llama.cpp and then at vLLM and the same script shows the batching gap.

## S4 · Foundry Local on the Windows NPU (slide 171)

Watch only. Foundry Local needs a Windows, macOS or Linux machine with the runtime installed (a codespace has no NPU and no GPU).
What to notice: it picks GPU, NPU or CPU by itself and still speaks the OpenAI API. At home, set
`FOUNDRY_LOCAL_BASE_URL` in `labs/.env` and run `04-local-media/python/solution/01_local_models.py`.

## S4 · a coding agent on a model you host (slide 179)

Watch only. This needs a local model server (Ollama / LM Studio) and a 27B-class model.
What to notice: it is the same agent harness, with only the endpoint changed. Watch where it struggles (long context, many tools).
The closest thing you can run here is the S4 tool loop above (slide 169): it is the same loop with a different model.

## S4 · Gemma 4 E4B hears you (slide 180)

Try it (cloud, not local):
```bash
python try/s4_hear.py "Which planet has the most moons?"
```
What to notice: a TTS voice speaks your question to `out/question.wav`, a transcription model hears it, and the chat
model answers what it heard. That takes three cloud models. Gemma 4 E4B does the hearing and the answering in one
local model, offline.

## S4 · Z-Image-Turbo in ComfyUI: seed and CFG live (slide 186)

Watch only for the real images (they need ComfyUI on a GPU). The method runs here with the ComfyUI stand-in:
```bash
python _tools/comfy_mock.py 8188 >/dev/null 2>&1 & M=$!; sleep 2; python 04-local-media/python/solution/03_one_knob.py 04-local-media/comfyui_workflows/01_txt2img_sdxl.json --knob seed --values 42 42 7; python 04-local-media/python/solution/03_one_knob.py 04-local-media/comfyui_workflows/01_txt2img_sdxl.json --knob cfg --values 2 7 15 --seed 42; kill $M
```
What to notice: the stand-in draws flat tiles that show the knobs it received, not real images. In
`out/one_knob/contact_seed.png` the same seed gives the same tile twice. In `contact_cfg.png` only CFG changes. Changing one knob at a time is the
craft principle, whatever the renderer.

## S4 · pose swap with ControlNet (slide 191)

Watch only. This needs SDXL, ControlNet and DWPose on a GPU in ComfyUI. The graph is
`04-local-media/comfyui_workflows/02_pose_lora_sdxl.json` if you want to read it.
What to notice: the skeleton says where, the prompt says who. At ControlNet strength 0.6 the prompt gets more say.

## S4 · Qwen3-TTS voice clone + Parakeet live captions (slide 201)

Try it (cloud voices, no cloning, no microphone):
```bash
python 04-local-media/python/solution/06_chain.py --topic "a radio host welcoming listeners" --image skip --voice coral --tone "a calm late-night radio host, slightly amused" --check
```
What to notice: `--tone` works like VoiceDesign. You describe a voice in words and hear it. `--check` is the caption
step: a transcription model writes down what it heard and counts the matching words. Voice cloning stays on stage, and
only with the speaker's own consent.

## S4 · the music-video chain, stage by stage + Wan2GP (slide 215)

Try it (text → image → voice → ears; no video and no Wan2GP, which need a GPU):
```bash
python 04-local-media/python/solution/06_chain.py --topic "a singer on stage at a tech conference" --writer Llama-4-Maverick-17B-128E-Instruct-FP8 --check
```
What to notice: each stage writes a file that the next stage reads (`out/chain_*.png`, `.wav`, `.json`). Swap one block
(`--writer`, `--voice`, `--tone`, `--image skip`) and the chain still works. Compare your runs in `out/chain.html`. You get
3 images per minute per key.

## S4 · Closer: an ACE-Step song about today (slide 223)

Try it (spoken, not sung):
```bash
python try/s4_song.py --tone "a slow, gravelly blues singer"
```
What to notice: block 1 is Lab 1 code. The agenda becomes tagged lyrics in `out/lyrics.txt`. Then gpt-4o-mini-tts
performs them as `out/song.wav`, with the recipe in `out/song.json`. On stage, ACE-Step 1.5 sings the same lyrics on one GPU.
