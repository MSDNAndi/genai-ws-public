# Setup — do this before the workshop day (45–60 minutes, mostly downloads)

**Building Stuff with GenAI — The Open Minded Workshop beyond OpenAI.** You will write code against cloud models
(Azure AI Foundry, through a workshop gateway) *and* models running on your own laptop. This page gets your machine
ready so the day is about building, not installing. If anything fails, run the checker (step 6) and send the
instructor its output.

## What you need

| | Required | Why |
|---|---|---|
| A laptop you can install software on | yes | admin rights help; a corporate proxy is fine if you know its address |
| **Python 3.12** (3.11 works) — easiest via **uv** | yes, for everyone | Labs 2 and 4 use Python-only tools; all labs have a Python version |
| **.NET 10 SDK** | for the C# track | labs are single-file apps: `dotnet run --file x.cs` |
| **Node.js 22+** (24 LTS recommended) | for the TypeScript track | plain `.mjs` files, no build step |
| **Ollama** + two models (~4.6 GB) | yes | the local half of the day (Lab 1 step 5, Lab 4) |
| VS Code (or any editor), git | recommended | |
| An MCP host: VS Code + GitHub Copilot, Claude Code, or LM Studio | optional | Lab 2 step 6 plugs your own server into it |
| LM Studio / Foundry Local | optional | more local runtimes to compare in Lab 4 |
| A GPU (NVIDIA ≥ 8 GB or Apple Silicon ≥ 16 GB) + ComfyUI | optional | local image generation in Lab 4; without a GPU you use the cloud path |

You do **not** need an Azure subscription, an OpenAI account or a credit card: on the day you get a personal key for
the workshop endpoint (valid for the event only).

## 1. Get the lab files
```bash
git clone <repository-url-from-the-invitation> bsgai-labs      # or unzip the download
cd bsgai-labs/labs
```
Every command below runs from this `labs` folder.

## 2. Python (everyone)
Recommended: [uv](https://docs.astral.sh/uv/getting-started/installation/) — it fetches Python 3.12 for you if your
machine has an older one, and installs packages much faster than pip. Install it once (Windows:
`winget install --id=astral-sh.uv -e` · macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh` · anywhere:
`pip install uv`), then:
```bash
uv venv --python 3.12                # creates labs/.venv
uv pip install -r requirements.txt   # ~350 MB; pinned versions tested together
```
Without uv: `python -m venv .venv`, activate it (below), `pip install -r requirements.txt`.

Run the lab scripts in either of two ways — the lab READMEs show the second:
`uv run 01_hello.py` (finds `labs/.venv` from any lab folder), or activate the environment once per terminal —
`source .venv/bin/activate` (Windows PowerShell: `.venv\Scripts\Activate.ps1`) — and use `python 01_hello.py`.
Windows: if activation is blocked, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.
Behind a proxy: set `HTTPS_PROXY=http://proxy:port` before installing (uv and pip both use it).

## 3. C# track: .NET 10 SDK
Install from https://dot.net, then pre-download the lab packages (so the labs also work on bad Wi-Fi):
```bash
dotnet --version                                   # 10.0.100 or newer
dotnet run --file 00-setup/check_env.cs            # first run restores packages (~20 s)
# optional, restores every C# lab once (~30 MB):
#   bash/zsh:   for f in */csharp/solution/*.cs; do dotnet build "$f"; done
#   PowerShell: Get-ChildItem */csharp/solution/*.cs | ForEach-Object { dotnet build $_.FullName }
```

## 4. TypeScript track: Node.js
Install Node 22+ (24 LTS recommended) from https://nodejs.org, then:
```bash
npm install                                        # in labs/ — one node_modules for all labs
```

## 5. Ollama and the local models (everyone)
Install from https://ollama.com, start it, then pull the two models the labs use:
```bash
ollama pull qwen3.5:4b        # 3.4 GB — chat + tool calling (smaller: qwen3.5:2b 2.7 GB, llama3.2:3b 2.0 GB)
ollama pull bge-m3            # 1.2 GB — embeddings for Lab 2 offline
ollama run qwen3.5:4b "Say hello in five words"
```
Optional, big: `ollama pull gemma4:e4b` (9.6 GB, also understands images and audio).
On a laptop CPU a 4B model answers in a few seconds once loaded. "Thinking" models are much slower — the labs switch
thinking off for local models (`OLLAMA_REASONING_EFFORT=none` in `.env`).

## 6. Your settings file and the checker
```bash
cp .env.example .env              # Windows: copy .env.example .env
```
Before the day you have no workshop key yet, so point the labs at Ollama to test everything end to end — edit `.env`:
```ini
GENAI_BASE_URL=http://localhost:11434/v1
GENAI_API_KEY=ollama
GENAI_MODEL=qwen3.5:4b
GENAI_REASONING_EFFORT=none
GENAI_EMBED_MODEL=bge-m3
```
Then run the checker for your track(s):
```bash
python 00-setup/check_env.py                       # everyone
dotnet run --file 00-setup/check_env.cs            # C# track
node 00-setup/check_env.mjs                        # TypeScript track
```
All green (✅) = you are ready. ⚠️ is fine (e.g. "labs/.env not found" when you use environment variables instead).
On the day you replace the first lines of `.env` with the values from your handout card and run the checker again.

## Troubleshooting
| Symptom | Fix |
|---|---|
| `401` / "Access denied due to missing subscription key" | key missing or mistyped; keep `GENAI_KEY_HEADER=api-key` |
| `404` / "DeploymentNotFound" | model name not deployed on the endpoint, or `GENAI_BASE_URL` does not end in `/openai/v1` (`/v1` for local servers) |
| `429` | your per-minute token limit — wait a minute, then retry |
| `403` (quota exceeded) | today's token quota for your key is used up — ask the instructor |
| "does not support reasoning_effort" | the chosen model is not a reasoning model: delete `GENAI_REASONING_EFFORT` from `.env` |
| Ollama is very slow | use a smaller model, keep `OLLAMA_REASONING_EFFORT=none`, close other heavy apps |
| SSL / certificate errors behind a corporate proxy | set `HTTPS_PROXY`; ask IT for the proxy CA and set `SSL_CERT_FILE` / `NODE_EXTRA_CA_CERTS` |
| Nothing works on the day (Wi-Fi) | the instructor runs an offline stand-in on the room network (`mock_openai_server.py`); point `GENAI_BASE_URL` at the address on the screen — answers are echoes, but every lab script runs. At home you can start it yourself: `python 00-setup/mock/mock_openai_server.py` → `http://127.0.0.1:8123/v1`, key `test`, model `mock-model` |

## Privacy
Prompts in the cloud labs go to the workshop endpoint in Azure; the local labs never leave your laptop. Don't paste
confidential data into the cloud labs. Your workshop key is personal, rate-limited and switched off after the event.
