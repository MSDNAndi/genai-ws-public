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
