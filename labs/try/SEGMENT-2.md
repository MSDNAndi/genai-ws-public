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
