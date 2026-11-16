"""Call one A2A Bazaar agent. Standard library only: works in any Python 3.9+, no pip install, no model key.

    python client.py                                  # list the agents (reads /registry)
    python client.py fx "Convert 120 USD to EUR"      # call one agent over A2A (JSON-RPC SendMessage)
    python client.py poet "a haiku about Orlando" --base https://bazaar.example.io --card

Base URL: --base, else $BAZAAR_URL, else http://localhost:8000. Room token (if the instructor set one): --token or
$BAZAAR_TOKEN. This is the whole protocol: GET the agent card, POST one JSON-RPC message to the URL it names.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
import uuid

p = argparse.ArgumentParser(description="Call an A2A Bazaar agent")
p.add_argument("agent", nargs="?", help="agent name, e.g. fx, poet, critic, summarizer")
p.add_argument("message", nargs="?", help="what to ask it")
p.add_argument("--base", default=os.getenv("BAZAAR_URL", "http://localhost:8000"))
p.add_argument("--token", default=os.getenv("BAZAAR_TOKEN", ""))
p.add_argument("--card", action="store_true", help="also print the agent card")
p.add_argument("--raw", action="store_true", help="print the raw JSON-RPC response")
args = p.parse_args()
base = args.base.rstrip("/")
UA = {"User-Agent": "bazaar-client/1.0"}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return json.load(r)


if not args.agent:
    reg = get(f"{base}/registry")
    print(f"{reg['bazaar']} - {reg['protocol']} - room token required: {reg['room_token_required']}\n")
    for a in reg["agents"]:
        print(f"  {a['name']:<11} {a['vendor']:<9} {a['model']}")
    print(f'\nnext: python client.py {reg["agents"][0]["name"]} "your message" --base {base}')
    sys.exit()

card = get(f"{base}/{args.agent}/.well-known/agent-card.json")          # 1. discovery
if args.card:
    print(json.dumps(card, indent=2))
endpoint = card["supportedInterfaces"][0]["url"]
body = {"jsonrpc": "2.0", "id": 1, "method": "SendMessage",                # 2. one JSON-RPC call
        "params": {"message": {"role": "ROLE_USER", "messageId": str(uuid.uuid4()),
                               "parts": [{"text": args.message or "Hello! What can you do?"}]}}}
headers = {**UA, "Content-Type": "application/json", "A2A-Version": "1.0"}
if args.token:
    headers["x-room-token"] = args.token
req = urllib.request.Request(endpoint, data=json.dumps(body).encode(), headers=headers, method="POST")
try:
    with urllib.request.urlopen(req, timeout=120) as r:
        resp = json.load(r)
except urllib.error.HTTPError as e:
    sys.exit(f"HTTP {e.code}: {e.read().decode(errors='replace')[:300]}")

if args.raw:
    print(json.dumps(resp, indent=2))
if "error" in resp:
    sys.exit(f"A2A error: {resp['error']}")
result = resp["result"]
obj = result.get("task") or result.get("message") or result
texts = [part.get("text", "") for art in obj.get("artifacts", []) for part in art.get("parts", [])]
if not texts:   # a direct message reply, or the agent's last message in the task history
    msgs = [obj] if "parts" in obj else [m for m in obj.get("history", []) if m.get("role") == "ROLE_AGENT"][-1:]
    texts = [part.get("text", "") for m in msgs for part in m.get("parts", [])]
state = obj.get("status", {}).get("state", "")
print(f"[{card['name']}] {state}".rstrip())
print("\n".join(t for t in texts if t).strip() or "(no text in reply - try --raw)")
