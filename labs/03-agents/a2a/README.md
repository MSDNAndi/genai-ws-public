# A2A Bazaar: agent-to-agent with the other side run by your neighbour

Each attendee runs one small agent in their codespace and makes the port public. Now everyone in the room (and the
instructor's orchestrator) can call it over **A2A 1.0**: an *agent card* at `/.well-known/agent-card.json` plus
one JSON-RPC method, `SendMessage`. Nothing to deploy and nothing new to install: the scripts use the Python standard
library plus the `openai` package the labs already have. Each agent runs on **its owner's** key and model.

## Attendees: three commands
Run these from the `labs/` virtual environment (`source labs/.venv/bin/activate` if your terminal doesn't have it yet).
```bash
cd labs/03-agents/a2a
python a2a_agent.py --persona pirate         # 1. start your agent (pirate, poet, chef, critic, eli5, guide)
#    2. make the port public: VS Code Ports tab -> right-click port 8100 -> Port Visibility -> Public
#       (or: gh codespace ports visibility 8100:public -c $CODESPACE_NAME, if gh is installed)
#       then paste the "public:" URL it printed into the chat / shared file
python a2a_call.py https://<neighbour>-8100.app.github.dev "What should we do tonight in Orlando?"   # 3. call a neighbour
```
- The agent prints its public URL, logs one line per request (watch your neighbours' calls arrive), and checks for
  up to 3 minutes whether the public URL answers (`[check] public URL answers`).
- `--public` makes the agent run the `gh` command itself (only if `gh` is installed). If it isn't, or the command
  fails, it prints the manual way. The "Make Public" button on the pop-up was not reliable when we tested; use the
  Ports tab.
- Your own persona: `python a2a_agent.py --name Haiku --skill haiku --instructions "Answer every question as a haiku."`
- Another brain: `GENAI_MODEL=DeepSeek-V4.1-Flash-1017 python a2a_agent.py --persona chef` (or `--model ...`).
  These models work on the workshop gateway: gpt-5-nano (default), gpt-5-mini, gpt-4o-mini, gpt-oss-120b,
  DeepSeek-V4.1-Flash-1017, grok-4-1-fast-non-reasoning, Llama-4-Maverick-17B-128E-Instruct-FP8.
  The agent sends no `temperature` and passes `GENAI_REASONING_EFFORT` like the labs (the workshop gateway drops it for models that reject it), so
  `GENAI_REASONING_EFFORT` from `labs/.env` is ignored here.
- Second agent in the same codespace: `--port 8101`.
- `python a2a_call.py <url> "..." --raw` prints the card and the raw JSON-RPC response: that is the whole protocol.

## Instructor
```bash
cd labs/03-agents/a2a
# collect the URLs in agents.txt (one per line, names or other text around them are fine), then:
python bazaar.py --cards           # the card table: who is up, which skill, which model
python bazaar.py --all             # everyone gets the same question in parallel, answers side by side
python bazaar.py                   # the model reads the cards, picks agents (function calling), calls them over
                                   # A2A and writes one answer that names who said what
python bazaar.py URL1 URL2 --ask "Plan a launch party: menu, toast, and a critique of the plan"
```
A dead agent, a private port or a slow agent never stops the run: it shows up as `DOWN` in the table or as an
`ERROR` / timeout in the answers (`--timeout`, default 60 s per call). Variation: ask half the room to start with
`GENAI_MODEL=DeepSeek-V4.1-Flash-1017` (or Llama, Grok): a multi-vendor team that nobody deployed.

Fallback when the room can't make ports public, or the Wi-Fi only lets a few through: **instructor hosts, attendees
call**. `demos/bazaar/` runs four agents on four vendors' models in one process (official `a2a-sdk` +
Agent Framework, behind one dev tunnel or a Container App), and its `client.py` is stdlib-only as well.

## Mock mode (no key, no gateway)
`A2A_MOCK=1` makes the agent answer with a persona echo instead of calling a model, and makes `bazaar.py` ask every
agent instead of using the orchestrator model. Use it when the gateway is down, or to test.
```bash
python test_a2a.py                 # everything on localhost in mock mode: one PASS/FAIL line per check
```
The two interop checks (official SDK client -> our agent, our client -> official SDK server) need the official
`a2a-sdk` in a **separate** virtual environment; the attendee scripts never need it:
```bash
python -m venv /tmp/a2a-venv && /tmp/a2a-venv/bin/pip install "a2a-sdk[http-server]>=1,<2" uvicorn httpx
A2A_SDK_PYTHON=/tmp/a2a-venv/bin/python python test_a2a.py
```

## Troubleshooting
| You see | Meaning / fix |
|---|---|
| `error: the port is not public ...` | The URL answered with 401 or the GitHub sign-in page. The **owner** sets it public: Ports tab -> right-click -> Port Visibility -> Public. |
| `connection refused` | No agent on that port (stopped, crashed, or another port). |
| `HTTP 404 ... no A2A agent there` | Wrong path or port. Paste the URL exactly as the agent printed it. |
| `agent error -32603: model call failed: PermissionDeniedError 403` | That model is not allowed on the gateway: pick one from the list above. |
| `agent error -32603: Busy ...` | The agent's own rate limit (`A2A_RATE_PER_MIN`, default 20 per minute). |
| `cannot listen on port 8100` | You already run an agent: stop it, or use `--port 8101`. |
| No answer, then timeout | The codespace went idle (stopped), or the model is slow. Try again; `--timeout 120`. |
| `GENAI_BASE_URL / GENAI_API_KEY not set` | Run from the codespace (the key is a codespace secret) or use `A2A_MOCK=1`. |

## Limits (say these out loud)
- **No authentication.** Anyone with your URL can call your agent and spend your key's quota (20k tokens per minute,
  500k per day). The agent caps itself at 20 messages per minute and 4 model calls at once, and accepts 16 KB per
  request. **Stop the agent after the demo (Ctrl+C) and set the port back to Private.**
- **Agent cards are untrusted input.** The orchestrator pastes card descriptions into its tool list; a card can carry
  a prompt injection (`demos/bazaar/` has a "shady" agent that shows exactly that).
- A small subset of A2A: non-streaming `SendMessage` only, text parts only, no tasks, no push notifications.
  The reply is a `Message`; our client also reads `Task` replies (artifacts/status/history) from other servers.
  A missing `A2A-Version` header is accepted as 1.0; `0.3` is refused with error -32009, like the official SDK.
- Foundry Agent Service also speaks A2A, but needs Entra sign-in, so it stays an instructor demo.
- A codespace that goes idle stops, and with it the agent.

## Files
| File | What |
|---|---|
| `a2a_agent.py` | the agent: card + JSON-RPC endpoint (`http.server`), personas, model call like Lab 1, mock mode |
| `a2a_call.py` | the client: fetch the card, `SendMessage`, print the reply; one-line errors. `bazaar.py` imports it |
| `bazaar.py` | the orchestrator: card table, `--all` side by side, or model-picked agents with attribution |
| `test_a2a.py` | localhost mock tests incl. the two official-SDK interop checks |
| `agents.txt` | the instructor's list of URLs |
