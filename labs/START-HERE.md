# Start here

Everything is installed. The terminal below is already in `labs/`. Run one of these:

```bash
python 01-hello-model/python/solution/01_hello.py                 # Python
dotnet run --file 01-hello-model/csharp/solution/01_hello.cs      # C#
node 01-hello-model/typescript/solution/01_hello.mjs              # TypeScript
```

You should see a model answer within a few seconds.

**It says the key is missing, or you get a 401:** open `labs/.env`, add the line `GENAI_API_KEY=<the key from the slide>`, save, and run the command again.

**Try another model:** in `labs/.env`, change `GENAI_MODEL=gpt-5-mini` to `gpt-6-astra` or `DeepSeek-V3.2`.

**The labs:** `01-hello-model`, `02-rag-mcp`, `03-agents` and `04-local-media`. Each has a `README.md`. The starter files are next to the `solution/` folder.

**When you're done:** stop the codespace at github.com/codespaces, so it doesn't use up your free hours. The workshop key stops working after today; the code keeps working with any OpenAI-compatible endpoint (see `.env.example`).
