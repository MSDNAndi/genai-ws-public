# Start here

Everything is installed. The terminal below is already in `labs/`. Pick **one** language, copy its command (hover, then the copy icon), paste it into the terminal and press Enter.

**Python**
```bash
python 01-hello-model/python/solution/01_hello.py
```

**C#**
```bash
dotnet run --file 01-hello-model/csharp/solution/01_hello.cs
```

**TypeScript**
```bash
node 01-hello-model/typescript/solution/01_hello.mjs
```

You should see a model answer within a few seconds. That's it — you're ready.

**Key missing, or a 401?** Open `labs/.env`, add the line `GENAI_API_KEY=<the key from your card>`, save, run the command again.

## The labs

`01-hello-model`, `02-rag-mcp`, `03-agents`, `04-local-media` — each folder has a `README.md`. You edit the starter files; the finished versions are in the `solution/` folder next to them.

## Try another model

In `labs/.env`, change `GENAI_MODEL=gpt-5-nano` to one of these. Nothing else to change — same key.

| Model | Vendor | Note |
|---|---|---|
| `gpt-5-nano` | OpenAI | default |
| `gpt-5-mini` | OpenAI | smarter |
| `gpt-4o-mini` | OpenAI | classic |
| `gpt-oss-120b` | OpenAI | open-weights |
| `DeepSeek-V4.1-Flash-1017` | DeepSeek | fast |
| `grok-4-1-fast-non-reasoning` | xAI | fast |
| `Llama-4-Maverick-17B-128E-Instruct-FP8` | Meta | open-weights |

**Edited `labs/.env` and nothing changed?** An environment variable with the same name wins over the file.
`python 00-setup/settings.py` shows where each setting comes from; `source 00-setup/use-dotenv.sh` makes this terminal use `labs/.env`.
Details: `00-setup/SETUP.md`.

## When you're done

Stop the codespace at [github.com/codespaces](https://github.com/codespaces), so it doesn't use up your free hours.

---

## After the workshop: your own endpoint

The workshop key stops working after today. The code works with any OpenAI-compatible endpoint, but more than the key changes. Edit these lines in `labs/.env`:

| Setting | Azure AI Foundry / Azure OpenAI | OpenAI |
|---|---|---|
| `GENAI_BASE_URL` | `https://<your-resource>.openai.azure.com/openai/v1` | `https://api.openai.com/v1` |
| `GENAI_API_KEY` | key from the Azure portal (Keys and Endpoint) | your OpenAI key |
| `GENAI_KEY_HEADER` | `api-key` | `Authorization` |
| `GENAI_MODEL`, `GENAI_MODEL_2` | your **deployment names** | model names, e.g. `gpt-5-nano` |
| `GENAI_EMBED_MODEL`, `GENAI_IMAGE_MODEL`, `GENAI_TTS_MODEL` | your deployment names | `text-embedding-3-large`, `gpt-image-1-mini`, `gpt-4o-mini-tts` |

On your own endpoint (or a local model), a model that rejects `reasoning_effort` needs the `GENAI_REASONING_EFFORT` line deleted. Local models (Ollama, LM Studio, Foundry Local) and every other option: `.env.example` and `00-setup/SETUP.md`.
