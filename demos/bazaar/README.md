# A2A Bazaar: a multi-agent meeting place, deployed

Four agents, four vendors' models, one URL. Each agent publishes an **A2A agent card**; `/registry` lists them;
an **orchestrator** discovers them at runtime and delegates. You call them from your codespace with one command,
outbound only, **without sending any key of yours**: the Bazaar pays for its own model calls.

| Agent | Model (via the class gateway) | Vendor | Does |
|---|---|---|---|
| `fx` | DeepSeek-V4.1-Flash-1017 | DeepSeek | currency conversion, names the rate |
| `poet` | Llama-4-Maverick-17B-128E-Instruct-FP8 | Meta | 6-line poem or toast |
| `critic` | grok-4-1-fast-non-reasoning | xAI | 3 concrete improvements |
| `summarizer` | gpt-5-nano | OpenAI | 3 bullets |
| `shady` (off) | gpt-4o-mini | OpenAI | the poisoned agent card (teaching moment) |

## Attendees: 3 commands

```bash
curl -sO https://<bazaar-url>/client.py                        # 1. get the client (stdlib only, no pip)
python3 client.py --base https://<bazaar-url>                  # 2. see who is in the Bazaar
python3 client.py poet "a haiku about Mondays" --base https://<bazaar-url> --token <room-token>   # 3. call one
```

`export BAZAAR_URL=https://<bazaar-url> BAZAAR_TOKEN=<room-token>` saves typing. Add `--card` to see the agent
card and `--raw` to see the JSON-RPC response. That is the whole protocol: GET a card, POST one `SendMessage`.

The same call with curl (A2A is just HTTP + JSON):

```bash
curl -s $BAZAAR_URL/fx/ -H 'Content-Type: application/json' -H 'A2A-Version: 1.0' -H "x-room-token: $BAZAAR_TOKEN" \
  -d '{"jsonrpc":"2.0","id":1,"method":"SendMessage","params":{"message":{"role":"ROLE_USER","messageId":"m1","parts":[{"text":"100 USD in EUR?"}]}}}'
```

Stretch: run the orchestrator yourself (its own model runs on *your* codespace key, the agents on the Bazaar's):

```bash
python3 -m venv /tmp/bazaar-venv && /tmp/bazaar-venv/bin/pip install -q -r demos/bazaar/requirements.txt
/tmp/bazaar-venv/bin/python demos/bazaar/orchestrator.py --base $BAZAAR_URL --token $BAZAAR_TOKEN
```

## Abuse protection (built in)

* **No attendee keys.** Model calls use the Bazaar's server-side key (a Container Apps secret). Attendees only need
  the URL.
* **Room token (optional).** If `BAZAAR_ROOM_TOKEN` is set, every POST must carry `x-room-token: <token>`
  (401 otherwise). Cards and `/registry` stay readable: discovery is public, use is gated. It is a speed bump
  for drive-by traffic, not authentication: it is on the slide.
* **Rate limits.** `BAZAAR_RATE_PER_MIN` per IP (default 12; one orchestrator run is 4-6 calls) and
  `BAZAAR_GLOBAL_PER_MIN` overall (default 120) return HTTP 429. `BAZAAR_MAX_CONCURRENT` (default 8) caps model calls
  in flight. Bodies over 8 KB get 413; each agent answers in at most ~350 tokens.
* **Blast radius.** The agents have no tools: no files, no shell, no web. Worst case is spent tokens, capped by the
  Bazaar's own APIM subscription, which you can suspend.

## Instructor run sheet

| When | Do | Say / show |
|---|---|---|
| T-15 min | `az containerapp update -g genaiclass-rg -n bazaar --min-replicas 1`; `python3 client.py fx "ping" --base $B --token $T` | |
| T-0 | Slide with the URL + room token. `curl -s $B/registry` | "Discovery: a registry of cards. Like DNS for agents." |
| +2 | `python3 client.py fx "..." --base $B --card` | the card: name, skills, `supportedInterfaces` (JSON-RPC, A2A 1.0) |
| +4 | Attendees run the 3 commands (5 min) | "you just called DeepSeek, Llama and Grok, without a key, over one protocol" |
| +10 | `python orchestrator.py --base $B --token $T` | the delegation trace: a gpt-5-nano agent picks fx, poet, critic, summarizer at runtime. Each tool is a remote agent on another vendor's model. |
| +14 | Note the context point | the remote agent sees only the message, not your transcript (as in sample 08) |
| +16 | **Poisoned card:** set `BAZAAR_SHADY=1` (deploy.md section 5), rerun the orchestrator | it calls `shady` first and ships it your request (and sometimes its system prompt): see the `!!!` line, and `curl $B/shady/loot` |
| +19 | `curl -s $B/shady/.well-known/agent-card.json` | "The card is untrusted input, like a web page in RAG. A2A gives you discovery, not trust." |
| +21 | `python orchestrator.py --base $B --token $T --safe` | the fix: an allow-list and *our own* tool descriptions. `shady` is skipped. |
| after | `--min-replicas 0`, later delete (deploy.md section 6) | |

If something breaks on stage: `client.py` needs only the standard library, and the orchestrator falls back to
answering itself when a tool fails (watch for `Error: Function failed` in the trace: that is usually a 429).

## Files

| File | What |
|---|---|
| `app.py` | the Bazaar: Starlette app mounting one A2A server per agent (`/<agent>/`), `/registry`, `/client.py`, the guard middleware |
| `orchestrator.py` | MAF `Agent` with `A2AAgent(...).as_tool()` per discovered card; prints the delegation trace; `--safe` |
| `client.py` | attendee client, standard library only |
| `requirements.txt` | pinned; installs alongside `labs/requirements.txt` (agent-framework-core 1.19.0) |
| `Dockerfile` | python:3.12-slim, non-root, no secrets |
| `deploy.md` | Azure Container Apps commands (not run), cost, kill switches, the codespace fallback |

Local run: `GENAI_BASE_URL=... GENAI_API_KEY=... python app.py` (port 8000; `BAZAAR_SHADY=1` adds the shady
agent), then `python client.py --base http://localhost:8000`.
