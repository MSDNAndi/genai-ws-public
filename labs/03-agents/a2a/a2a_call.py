"""Call one A2A agent: fetch its card, send one message, print the reply. Standard library only.

    python a2a_call.py https://<codespace>-8100.app.github.dev "What should I see in Orlando?"
    python a2a_call.py http://localhost:8100 "Hello"                    # your own agent
    python a2a_call.py <url> "Hello" --raw                               # also print the JSON-RPC exchange

This is the whole protocol (A2A 1.0, JSON-RPC binding):
    1. GET  <url>/.well-known/agent-card.json  -> who are you, what can you do, where do I POST?
    2. POST <card url>  {"jsonrpc": "2.0", "method": "SendMessage", "params": {"message": {...}}}
bazaar.py imports the functions below.
"""
from __future__ import annotations

import argparse
import json
import re
import socket
import sys
import urllib.error
import urllib.request
import uuid

CARD_PATH = "/.well-known/agent-card.json"
HEADERS = {"User-Agent": "a2a-bazaar/1.0", "Accept": "application/json"}
NOT_PUBLIC_HELP = ("the port is not public. Owner: VS Code Ports tab -> right-click the port -> Port Visibility -> "
                   "Public   (or: gh codespace ports visibility {port}:public -c $CODESPACE_NAME)")


class A2AError(Exception):
    """One-line, human-readable failure (unreachable, not public, not an agent, JSON-RPC error ...)."""


def base_url(url: str) -> str:
    """Accept the agent URL, the card URL, or a bare host:port."""
    url = url.strip().rstrip("/")
    if not re.match(r"^https?://", url):
        url = ("http://" if url.startswith(("localhost", "127.", "0.0.0.0")) else "https://") + url
    if url.endswith(CARD_PATH):
        url = url[: -len(CARD_PATH)]
    return url.rstrip("/")


def _not_public(url: str) -> A2AError:
    m = re.match(r"https://(.+)-(\d+)\.[^/]+", url)
    port = m.group(2) if m else "<port>"
    return A2AError(NOT_PUBLIC_HELP.format(port=port))


def _http(url: str, body: dict | None, timeout: float, extra_headers: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    headers = {**HEADERS, **(extra_headers or {})}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            ctype = r.headers.get("Content-Type", "")
            raw = r.read(1_000_000)
            final_url = r.geturl()
    except urllib.error.HTTPError as e:
        text = e.read(2000).decode("utf-8", "replace")
        if e.code in (401, 403) or "<html" in text[:500].lower():   # private codespace port: 401 or sign-in page
            raise _not_public(url) from None
        if e.code == 404:
            raise A2AError(f"HTTP 404 at {url}: no A2A agent there (wrong URL or port?)") from None
        raise A2AError(f"HTTP {e.code} at {url}: {text.strip()[:150]}") from None
    except urllib.error.URLError as e:
        reason = getattr(e, "reason", e)
        if isinstance(reason, ConnectionRefusedError):
            raise A2AError(f"cannot reach {url}: connection refused (is the agent running, right port?)") from None
        if isinstance(reason, (socket.timeout, TimeoutError)):
            raise A2AError(f"timeout after {timeout:.0f}s at {url}") from None
        raise A2AError(f"cannot reach {url}: {reason}") from None
    except (socket.timeout, TimeoutError):
        raise A2AError(f"timeout after {timeout:.0f}s at {url}") from None
    except (ConnectionError, OSError) as e:
        raise A2AError(f"cannot reach {url}: {e}") from None
    except (ValueError, UnicodeError) as e:          # e.g. a URL with a typo in the host name
        raise A2AError(f"not a valid URL: {url} ({e})") from None
    text = raw.decode("utf-8", "replace")
    if "html" in ctype.lower() or text.lstrip()[:1] == "<" or "github.com/login" in final_url:
        raise _not_public(url)               # the answer is a web page (GitHub sign-in), not JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        raise A2AError(f"{url} did not answer JSON: {text.strip()[:100]!r}") from None


def fetch_card(url: str, timeout: float = 15) -> dict:
    card = _http(base_url(url) + CARD_PATH, None, timeout)
    if not isinstance(card, dict) or "name" not in card:
        raise A2AError(f"{url}: that JSON is not an A2A agent card (no 'name')")
    return card


def endpoint_of(card: dict, fallback: str) -> str:
    """The JSON-RPC URL from the card (A2A 1.0: supportedInterfaces; 0.3: url)."""
    for itf in card.get("supportedInterfaces") or []:
        if str(itf.get("protocolBinding", "JSONRPC")).upper() == "JSONRPC" and itf.get("url"):
            return itf["url"]
    return card.get("url") or base_url(fallback) + "/"


def skills_of(card: dict) -> str:
    return ", ".join(s.get("name") or s.get("id", "?") for s in card.get("skills") or []) or "-"


def send_message(endpoint: str, text: str, timeout: float = 90, context_id: str | None = None) -> tuple[str, dict]:
    """SendMessage over JSON-RPC. Returns (reply text, raw JSON-RPC response)."""
    message = {"messageId": str(uuid.uuid4()), "role": "ROLE_USER", "parts": [{"text": text}]}
    if context_id:
        message["contextId"] = context_id
    body = {"jsonrpc": "2.0", "id": str(uuid.uuid4()), "method": "SendMessage",
            "params": {"message": message, "configuration": {"acceptedOutputModes": ["text/plain"]}}}
    resp = _http(endpoint, body, timeout, {"A2A-Version": "1.0"})
    if "error" in resp:
        err = resp["error"] or {}
        raise A2AError(f"agent error {err.get('code')}: {err.get('message')}"
                       + (f" ({str(err.get('data'))[:120]})" if isinstance(err.get("data"), str) else ""))
    return reply_text(resp.get("result") or {}), resp


def reply_text(result: dict) -> str:
    """Text from a SendMessageResponse: {"message": {...}} or {"task": {...}} (artifacts, status, history)."""
    def texts(parts):
        return [p["text"] for p in parts or [] if isinstance(p, dict) and p.get("text")]
    if "message" in result:
        return "\n".join(texts(result["message"].get("parts")))
    task = result.get("task") or result
    out = [t for a in task.get("artifacts") or [] for t in texts(a.get("parts"))]
    if not out:
        out = texts((task.get("status") or {}).get("message", {}).get("parts"))
    if not out:
        agent_msgs = [m for m in task.get("history") or [] if m.get("role") in ("ROLE_AGENT", "agent")]
        out = texts(agent_msgs[-1].get("parts")) if agent_msgs else []
    state = (task.get("status") or {}).get("state", "")
    if not out and state:
        return f"(no text; task state {state})"
    return "\n".join(out)


def main() -> None:
    p = argparse.ArgumentParser(description="Call one A2A agent (card + SendMessage)")
    p.add_argument("url", help="agent URL, e.g. https://<codespace>-8100.app.github.dev")
    p.add_argument("message", nargs="?", default="Hello! Who are you and what can you do?")
    p.add_argument("--timeout", type=float, default=90)
    p.add_argument("--raw", action="store_true", help="print the card and the raw JSON-RPC response")
    args = p.parse_args()
    try:
        card = fetch_card(args.url)
        endpoint = endpoint_of(card, args.url)
        print(f"agent:  {card['name']} - {card.get('description', '')}")
        print(f"skills: {skills_of(card)}")
        if args.raw:
            print(json.dumps(card, indent=2))
        try:
            text, resp = send_message(endpoint, args.message, args.timeout)
        except A2AError as e:
            if base_url(endpoint) == base_url(args.url) or "agent error" in str(e):
                raise
            text, resp = send_message(base_url(args.url) + "/", args.message, args.timeout)  # card URL unreachable
        if args.raw:
            print(json.dumps(resp, indent=2))
        print(f"\n[{card['name']}] {text or '(empty reply)'}")
    except A2AError as e:
        sys.exit(f"error: {e}")
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
