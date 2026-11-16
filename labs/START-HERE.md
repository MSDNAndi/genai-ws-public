# Start here

Everything is installed. The terminal below is already in `labs/`. Run one of these:

```bash
python 01-hello-model/python/solution/01_hello.py                 # Python
dotnet run --file 01-hello-model/csharp/solution/01_hello.cs      # C#
node 01-hello-model/typescript/solution/01_hello.mjs              # TypeScript
```

You should see a model answer within a few seconds.

**It says the key is missing, or you get a 401:** open `labs/.env`, add the line `GENAI_API_KEY=<the key from your card>`, save, and run the command again.

**Try another model:** in `labs/.env`, change `GENAI_MODEL=gpt-5-mini` to `gpt-6-astra` or `DeepSeek-V3.2`.

**The labs:** `01-hello-model`, `02-rag-mcp`, `03-agents` and `04-local-media`. Each has a `README.md`. The starter files are next to the `solution/` folder.

**When you're done:** stop the codespace at github.com/codespaces, so it doesn't use up your free hours.

## Your own endpoint (after the workshop, or instead of the workshop key)

The workshop key stops working after the workshop. The code works with any OpenAI-compatible endpoint, but a key alone is not enough: the endpoint URL, how the key is sent, and the model (on Azure: deployment) names all change. Edit these lines in `labs/.env`:

| Setting | Azure AI Foundry / Azure OpenAI | OpenAI |
|---|---|---|
| `GENAI_BASE_URL` | `https://<your-resource>.openai.azure.com/openai/v1` | `https://api.openai.com/v1` |
| `GENAI_API_KEY` | key from the Azure portal (Keys and Endpoint) | your OpenAI key |
| `GENAI_KEY_HEADER` | `api-key` | `Authorization` |
| `GENAI_MODEL`, `GENAI_MODEL_2` | your **deployment names** | model names, e.g. `gpt-5-mini` |
| `GENAI_EMBED_MODEL`, `GENAI_IMAGE_MODEL`, `GENAI_TTS_MODEL` | your deployment names | `text-embedding-3-large`, `gpt-image-1-mini`, `gpt-4o-mini-tts` |

Non-reasoning model (e.g. `gpt-4.1`)? Delete the `GENAI_REASONING_EFFORT` line. Local models (Ollama, LM Studio, Foundry Local) and every other option are explained in `.env.example`.

**Important in a codespace:** a key entered on the "Create codespace" page wins over `labs/.env`. Remove it at github.com/settings/codespaces (Secrets), or run `unset GENAI_API_KEY` in your terminal (that terminal only), then run `python 00-setup/check_env.py` to confirm the new settings.
