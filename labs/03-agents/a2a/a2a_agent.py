"""Your own A2A agent in one command: an agent card + a JSON-RPC endpoint (A2A 1.0), stdlib + openai only.

    python a2a_agent.py --persona pirate                  # port 8100; in a codespace it prints your public URL
    python a2a_agent.py --persona chef --port 8101 --public    # also runs the gh command that makes the port public
    python a2a_agent.py --name Haiku --skill haiku --instructions "Answer every question as a haiku."
    A2A_MOCK=1 python a2a_agent.py --persona poet         # no model call: a persona echo (test mode / no gateway)

Model settings exactly like the labs (labs/.env, environment wins): GENAI_BASE_URL, GENAI_API_KEY, GENAI_MODEL
(default gpt-5-nano), `api-key` header when GENAI_KEY_HEADER=api-key. No temperature, no reasoning_effort: some
models on the gateway reject one or the other.

    GET  /.well-known/agent-card.json   the agent card (discovery)
    POST /                              JSON-RPC 2.0: method "SendMessage" (the only one we implement)

No authentication: anyone with your URL can spend your key's quota. Stop the agent (Ctrl+C) after the demo.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import uuid
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

CARD_PATH = "/.well-known/agent-card.json"
MAX_BODY = 16_384           # bytes per request: a question, not a novel
MAX_INPUT = 2_000           # characters of the question that reach the model
RATE_PER_MIN = int(os.getenv("A2A_RATE_PER_MIN", "20"))      # SendMessage calls per minute, all callers together
MAX_PARALLEL = int(os.getenv("A2A_MAX_PARALLEL", "4"))      # model calls in flight

PERSONAS = {
    "pirate": ("Pirate", "pirate-talk", "Answers any question in the voice of a cheerful pirate captain.",
               "You are a cheerful pirate captain. Answer the question correctly, but in pirate speak. "
               "At most 80 words.", ["fun", "voice"], ["What is an API?"]),
    "poet": ("Poet", "short-poem", "Turns any topic into a short poem (max 6 lines).",
             "You are a poet. Answer with a poem of at most 6 short lines about the topic you are given. No preamble.",
             ["creative", "writing"], ["A poem about Orlando in November"]),
    "chef": ("Chef", "recipe", "Suggests a quick dish or menu for any occasion, with a 3-step method.",
             "You are a practical chef. Suggest one dish that fits the request, list key ingredients and give a "
             "3-step method. At most 90 words.", ["food", "planning"], ["Dinner for 6 developers after a workshop"]),
    "critic": ("Critic", "critique", "Reviews a plan, text or idea and returns 3 concrete improvements.",
               "You are a sharp but kind critic. Return exactly 3 numbered, concrete improvements to what you are "
               "given. No preamble, at most 80 words.", ["review"], ["Our plan: ship on Friday at 5pm"]),
    "eli5": ("Explainer", "explain-simply", "Explains any technical idea so a ten-year-old gets it, with an analogy.",
             "You explain things to a ten-year-old. Use one everyday analogy, no jargon, at most 70 words.",
             ["teaching", "explain"], ["What is agent-to-agent communication?"]),
    "guide": ("Orlando Guide", "local-tips", "Local tips for Orlando: food, sights, getting around, weather.",
              "You are a friendly Orlando local guide. Give 3 concrete tips that fit the question, each one line. "
              "Say when something may have changed. At most 90 words.", ["travel", "orlando"],
              ["One free evening near the convention center: what to do?"]),
}

# ---- settings, like the labs: every .env from here upward (nearest wins), environment variables win ----------------
_here = Path(__file__).resolve()
for _folder in [*_here.parents, Path.cwd(), *Path.cwd().parents]:
    if (_folder / ".env").is_file():
        try:
            from dotenv import load_dotenv
            load_dotenv(_folder / ".env")
        except ImportError:                       # stdlib fallback: KEY=value lines, never overrides the environment
            for line in (_folder / ".env").read_text(encoding="utf-8", errors="replace").splitlines():
                k, sep, v = line.strip().partition("=")
                if sep and not k.startswith("#") and k.strip() not in os.environ:
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")

MOCK = os.getenv("A2A_MOCK", "") == "1"


def public_url(port: int) -> str | None:
    name, domain = os.getenv("CODESPACE_NAME"), os.getenv("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN")
    return f"https://{name}-{port}.{domain}" if name and domain else None


class Agent:
    def __init__(self, args):
        if args.persona:
            title, skill, desc, instr, tags, examples = PERSONAS[args.persona]
        else:
            title, skill, desc, instr, tags, examples = "Agent", "answer", "Answers questions.", \
                "You are a helpful, concise assistant. At most 80 words.", ["general"], []
        self.name = args.name or title
        self.skill = args.skill or skill
        self.instructions = args.instructions or instr
        self.description = args.description or (desc if not args.instructions else f"{self.skill}: {args.instructions[:150]}")
        self.tags, self.examples = tags, examples
        self.model = args.model or os.getenv("GENAI_MODEL") or "gpt-5-nano"
        self.port = args.port
        self.url = (args.public_url or public_url(args.port) or f"http://localhost:{args.port}").rstrip("/") + "/"
        self.calls: deque[float] = deque()
        self.lock = threading.Lock()
        self.slots = threading.BoundedSemaphore(MAX_PARALLEL)
        self.client = None
        if not MOCK:
            if not os.getenv("GENAI_API_KEY") or not os.getenv("GENAI_BASE_URL"):
                sys.exit("error: GENAI_BASE_URL / GENAI_API_KEY not set (labs/.env or the codespace secret). "
                         "No key? Run with A2A_MOCK=1 for a persona echo.")

    def connect(self) -> None:
        """Create the model client (after the banner: importing openai can take a few seconds)."""
        if MOCK:
            return
        from openai import OpenAI
        key = os.environ["GENAI_API_KEY"]
        headers = {"api-key": key} if os.getenv("GENAI_KEY_HEADER", "api-key") == "api-key" else None
        self.client = OpenAI(base_url=os.environ["GENAI_BASE_URL"], api_key=key, default_headers=headers,
                             timeout=75, max_retries=1)

    def card(self) -> dict:
        return {
            "name": self.name,
            "description": f"{self.description} (model: {'mock' if MOCK else self.model})",
            "version": "1.0.0",
            "supportedInterfaces": [{"url": self.url, "protocolBinding": "JSONRPC", "protocolVersion": "1.0"}],
            "capabilities": {"streaming": False, "pushNotifications": False},
            "defaultInputModes": ["text/plain"],
            "defaultOutputModes": ["text/plain"],
            "skills": [{"id": self.skill, "name": self.skill, "description": self.description,
                        "tags": self.tags, "examples": self.examples}],
        }

    def allow(self) -> bool:
        now = time.monotonic()
        with self.lock:
            while self.calls and now - self.calls[0] > 60:
                self.calls.popleft()
            if len(self.calls) >= RATE_PER_MIN:
                return False
            self.calls.append(now)
            return True

    def answer(self, question: str) -> tuple[str, int]:
        if MOCK:
            return f"[{self.name}, mock] ({self.skill}) You asked: {question[:200]}", 0
        with self.slots:
            # GENAI_REASONING_EFFORT=low (labs/.env) keeps gpt-5 models fast; the workshop gateway drops it for models
            # that reject it, so switching GENAI_MODEL is all you ever change
            extra = {"reasoning_effort": os.environ["GENAI_REASONING_EFFORT"]} if os.getenv("GENAI_REASONING_EFFORT") else {}
            r = self.client.chat.completions.create(model=self.model, **extra, messages=[
                {"role": "system", "content": self.instructions + " You are one agent in a room of agents; another "
                 "agent or a person is calling you. Be brief."},
                {"role": "user", "content": question[:MAX_INPUT]}])
        text = (r.choices[0].message.content or "").strip() or "(the model returned an empty answer)"
        return text, (r.usage.total_tokens if r.usage else 0)


def rpc_error(rid, code: int, message: str, data=None) -> dict:
    err = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": rid, "error": err}


def make_handler(agent: Agent):
    class Handler(BaseHTTPRequestHandler):
        server_version = "a2a-bazaar/1.0"

        def log_message(self, *a):          # we print our own one line per request
            pass

        def _who(self) -> str:
            return (self.headers.get("X-Forwarded-For", "").split(",")[0].strip() or self.client_address[0])

        def _send(self, status: int, obj, ctype="application/json"):
            body = obj if isinstance(obj, bytes) else json.dumps(obj).encode()
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        def _log(self, what: str):
            print(f"{time.strftime('%H:%M:%S')}  {self._who():<15}  {what}", flush=True)

        def do_GET(self):
            path = self.path.split("?")[0]
            if path in (CARD_PATH, "/.well-known/agent.json"):
                self._log("card")
                return self._send(200, agent.card())
            if path == "/":
                return self._send(200, f"A2A agent '{agent.name}'. Card: {agent.url.rstrip('/')}{CARD_PATH}\n"
                                  "POST JSON-RPC 2.0 (method SendMessage) to this URL.\n".encode(), "text/plain")
            self._send(404, {"error": "not found", "card": CARD_PATH})

        def do_OPTIONS(self):
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, A2A-Version")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.end_headers()

        def do_POST(self):
            t0 = time.monotonic()
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                self._log(f"rejected: {length} bytes")
                return self._send(200, rpc_error(None, -32600, "Payload too large"))
            try:
                body = json.loads(self.rfile.read(length) or b"null")
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                self._log("rejected: not JSON")
                return self._send(200, rpc_error(None, -32700, "Parse error", str(e)))
            rid = body.get("id") if isinstance(body, dict) else None
            if not isinstance(body, dict) or body.get("jsonrpc") != "2.0" or not isinstance(body.get("method"), str):
                return self._send(200, rpc_error(rid, -32600, "Invalid Request"))
            method = body["method"]
            version = self.headers.get("A2A-Version", "").strip()
            if version and not version.startswith("1."):    # no header: we assume 1.0 (lenient)
                self._log(f"rejected: A2A-Version {version}")
                return self._send(200, rpc_error(rid, -32009, f"A2A version '{version}' is not supported by this "
                                                 "handler. Expected version '1.0'."))
            if method != "SendMessage":
                self._log(f"rejected: method {method}")
                return self._send(200, rpc_error(rid, -32601, "Method not found"))
            msg = (body.get("params") or {}).get("message") if isinstance(body.get("params"), dict) else None
            parts = msg.get("parts") if isinstance(msg, dict) else None
            if not isinstance(parts, list) or msg.get("role") not in ("ROLE_USER", "user"):
                return self._send(200, rpc_error(rid, -32602, "Invalid params",
                                                 "params.message needs role ROLE_USER and a parts list"))
            question = "\n".join(p.get("text", "") for p in parts if isinstance(p, dict) and p.get("text")).strip()
            if not question:
                return self._send(200, rpc_error(rid, -32602, "Invalid params", "no text part in the message"))
            if not agent.allow():
                self._log(f"rate limited ({RATE_PER_MIN}/min)")
                return self._send(200, rpc_error(rid, -32603, f"Busy: this agent answers {RATE_PER_MIN} "
                                                 "messages per minute. Try again in a minute."))
            try:
                text, tokens = agent.answer(question)
            except Exception as e:                  # one line, never the key: class + status + short message
                status = getattr(e, "status_code", "")
                self._log(f"\"{question[:50]}\"  -> model error {type(e).__name__} {status}")
                detail = str(e).replace(os.getenv("GENAI_API_KEY") or "\0", "***")[:160]
                return self._send(200, rpc_error(rid, -32603, f"model call failed: {type(e).__name__} {status}"
                                                 .strip() + f" ({agent.model})", detail))
            reply = {"messageId": str(uuid.uuid4()), "role": "ROLE_AGENT", "parts": [{"text": text}]}
            if msg.get("contextId"):
                reply["contextId"] = msg["contextId"]
            self._log(f"\"{question[:50].replace(chr(10), ' ')}\"  -> {time.monotonic() - t0:.1f}s"
                      + (f", {tokens} tokens" if tokens else ""))
            self._send(200, {"jsonrpc": "2.0", "id": rid, "result": {"message": reply}})

    return Handler


def make_public(port: int) -> None:
    name = os.getenv("CODESPACE_NAME")
    manual = f"   do it by hand: VS Code Ports tab -> right-click port {port} -> Port Visibility -> Public"
    if not shutil.which("gh"):
        print(f"  [public] gh is not installed here.\n{manual}", flush=True)
        return
    time.sleep(2)                                   # let the codespace notice the new port first
    for attempt in (1, 2):
        r = subprocess.run(["gh", "codespace", "ports", "visibility", f"{port}:public", "-c", name],
                           capture_output=True, text=True, timeout=60)
        if r.returncode == 0:
            print(f"  [public] port {port} is now public", flush=True)
            return
        time.sleep(5)
    print(f"  [public] gh failed: {(r.stderr or r.stdout).strip()[:160]}\n{manual}", flush=True)


def check_public(url: str, port: int) -> None:
    """Poll our own public card URL until it answers JSON (i.e. the port is public); print the result once."""
    deadline = time.monotonic() + 180
    said_private = False
    while time.monotonic() < deadline:
        try:
            req = urllib.request.Request(url.rstrip("/") + CARD_PATH, headers={"User-Agent": "a2a-bazaar/1.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                if "json" in r.headers.get("Content-Type", ""):
                    print(f"  [check] public URL answers: {url}  <- share it", flush=True)
                    return
        except Exception:
            pass
        if not said_private:
            print(f"  [check] public URL does not answer yet (port {port} still private?) - checking for 3 min",
                  flush=True)
            said_private = True
        time.sleep(6)
    print(f"  [check] still not public after 3 min. Ports tab -> right-click port {port} -> Port Visibility -> "
          "Public", flush=True)


def main() -> None:
    p = argparse.ArgumentParser(description="Run your own A2A agent (stdlib + openai)")
    p.add_argument("--persona", choices=sorted(PERSONAS), help="a preset: " + ", ".join(sorted(PERSONAS)))
    p.add_argument("--name", help="agent name on the card (default: the persona's)")
    p.add_argument("--skill", help="skill id on the card")
    p.add_argument("--description", help="one sentence for the card: what you are good at")
    p.add_argument("--instructions", help="system prompt (your own persona)")
    p.add_argument("--model", help="model (default: GENAI_MODEL, else gpt-5-nano)")
    p.add_argument("--port", type=int, default=int(os.getenv("A2A_PORT", "8100")))
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--public", action="store_true", help="in a codespace: run gh to make the port public")
    p.add_argument("--public-url", default=os.getenv("A2A_PUBLIC_URL"), help="URL to put in the card (override)")
    p.add_argument("--no-check", action="store_true", help="do not poll the public URL")
    args = p.parse_args()
    if not (args.persona or args.instructions):
        args.persona = "pirate"
    agent = Agent(args)
    try:
        server = ThreadingHTTPServer((args.host, args.port), make_handler(agent))
    except OSError as e:
        sys.exit(f"error: cannot listen on port {args.port} ({e.strerror}). Another agent running? Try --port "
                 f"{args.port + 1}")
    server.daemon_threads = True
    pub = public_url(args.port)
    print(f"A2A agent '{agent.name}' (skill {agent.skill}, model {'MOCK' if MOCK else agent.model}) "
          f"on {args.host}:{args.port}")
    print(f"  local:  http://localhost:{args.port}/")
    if pub:
        print(f"  public: {pub}/   <- paste this into the chat / shared file")
        print(f"  make the port public (once): VS Code Ports tab -> right-click port {args.port} -> "
              "Port Visibility -> Public")
        print(f"     or: gh codespace ports visibility {args.port}:public -c $CODESPACE_NAME"
              + ("" if shutil.which("gh") else "   (gh is not installed in this codespace)"))
    print(f"  try it:  python a2a_call.py {(pub or f'http://localhost:{args.port}')} \"Who are you?\"")
    print("  No authentication: anyone with the URL spends your key's quota. Ctrl+C stops the agent.\n", flush=True)
    if pub and args.public:
        threading.Thread(target=make_public, args=(args.port,), daemon=True).start()
    if pub and not args.no_check:
        threading.Thread(target=check_public, args=(pub, args.port), daemon=True).start()
    agent.connect()
    print(f"ready - waiting for calls (one line per request)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped. Set the port back to private (Ports tab -> Port Visibility -> Private).")


if __name__ == "__main__":
    main()
