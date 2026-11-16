# How today's models are deployed: cloud gateway and local runtime, same API

Every lab talks to "an OpenAI-compatible endpoint": a base URL, a key, a model name. Behind that one interface sit two
very different deployments. Today you use the first; the second runs on your own machine.

## 1. The workshop endpoint: models behind a gateway in Azure

```
your codespace ──HTTPS, api-key: <your card key>──▶  API gateway (Azure API Management)  ──managed identity──▶  Azure AI Foundry
  (labs/.env:                                         · one key per attendee (100 keys)                        · gpt-5-nano, gpt-oss-120b,
   GENAI_BASE_URL,                                    · tokens/min + tokens/day per key                          DeepSeek-V4.1-Flash, grok-4.1-fast,
   GENAI_MODEL)                                       · model allowlist (cheap models only)                      Llama-4-Maverick, embeddings, images
                                                      · strips your key, signs in as itself                    · speech models in a 2nd region
                                                      · token metrics per key (cost per person)
```

What each piece does, and why a real company would do the same:

| Concern | How it is solved today | Production lesson |
|---|---|---|
| Who may call? | a personal key per attendee, revocable in seconds | never hand out the model provider's own key |
| Cost | allowlist of cheap models (others get `403 model_not_allowed`), 500k tokens/day per key | put limits *in front of* the model, not in the client |
| Fairness | 20k tokens/min per key; images 3/min, speech 6/min | one heavy user must not starve the room |
| Secrets | the gateway removes your key and calls Foundry with its own managed identity — no Foundry key exists anywhere in the labs | identity beats keys |
| Several regions | text models in one region, speech in another; the gateway routes by path | the client never knows |
| Observability | the gateway emits token usage per key | you can show cost per team, per app, per user |
| Vendor choice | five model families behind one URL; switch with `GENAI_MODEL` | the app does not change when the model does |

Try it: `python 00-setup/check_env.py` shows the endpoint and model; ask for an expensive model
(`GENAI_MODEL=gpt-5.5 python 01-hello-model/python/solution/01_hello.py`) and read the gateway's answer.

## 2. Local deployment: the same API on your own hardware

The labs only need a different base URL — the code stays the same (Lab 1 step 5, Lab 4 step 1):

| Runtime | Start | Base URL for `labs/.env` |
|---|---|---|
| Ollama | `ollama serve` (then `ollama pull qwen3.5:4b`) | `http://localhost:11434/v1` |
| LM Studio | Developer tab → Start server | `http://localhost:1234/v1` |
| Azure AI Foundry Local | `foundry model run <model>`; `foundry service status` prints the URL | the URL it prints + `/v1` |
| llama.cpp | `llama-server -m model.gguf --port 8091` | `http://localhost:8091/v1` |

"Deployed" locally means: the model file is on your disk, a server process exposes it on a port, and you decide who
can reach that port. A GPU box in your office running Ollama or Foundry Local *is* a deployment — put the same kind of
gateway in front of it and you have your own private endpoint.

What local shows that a cloud endpoint hides:

- **The model is a file.** Size on disk, quantization (Q4 vs Q8 vs FP16), and what that does to quality and memory.
- **Your hardware is the limit.** Tokens per second on CPU vs GPU, RAM/VRAM, and what happens when the model doesn't fit.
- **No meter running.** No per-token cost, no rate limits. Offline works, and prompts never leave the machine.
- **All the knobs.** Sampling settings, "thinking" on/off (`OLLAMA_REASONING_EFFORT=none`), and context length are yours.
- **The trade-off is real.** The same Lab 1 question on a 2–4B local model vs a cloud model: speed, quality, and the
  "small model explains *API* tokens" moment.

Codespaces have no GPU and no local runtime, so the local half is an instructor demo today; `labs/00-setup/SETUP.md`
shows how to set it up on your laptop afterwards.

## 3. Which one when?

| Need | Cloud endpoint | Local runtime |
|---|---|---|
| Best quality, newest models, scale | ✔ | |
| Data must not leave the device / offline | | ✔ |
| Predictable cost at high volume | depends | ✔ (hardware is the cost) |
| Zero setup for 60 people today | ✔ | |
| Learn how models actually behave | ✔ | ✔✔ |

Most real systems mix both behind one interface — which is exactly why every lab reads just `GENAI_BASE_URL`,
`GENAI_API_KEY` and `GENAI_MODEL`.
