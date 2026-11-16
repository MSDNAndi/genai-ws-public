"""Everything on localhost in mock mode (no model, no key). One PASS / FAIL / SKIP line per check.

    python test_a2a.py
    A2A_SDK_PYTHON=/tmp/a2a-venv/bin/python python test_a2a.py      # + the two official-SDK interop checks

The interop checks need the official SDK, in a SEPARATE venv (never labs/.venv; the attendee scripts do not need it):
    python -m venv /tmp/a2a-venv && /tmp/a2a-venv/bin/pip install "a2a-sdk[http-server]>=1,<2" uvicorn httpx
If the current Python already has `a2a` installed, it is used.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = sys.executable
RESULTS: list[bool] = []
PROCS: list[subprocess.Popen] = []
ENV = {**os.environ, "A2A_MOCK": "1", "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"}
for k in ("CODESPACE_NAME", "GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN", "A2A_PUBLIC_URL"):
    ENV.pop(k, None)                       # test as on a laptop, even inside a codespace


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail and not ok else ""), flush=True)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_port(port: int, secs: float = 20) -> bool:
    end = time.monotonic() + secs
    while time.monotonic() < end:
        try:
            with socket.create_connection(("127.0.0.1", port), 0.5):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def start(cmd: list[str], env=None) -> subprocess.Popen:
    p = subprocess.Popen(cmd, cwd=HERE, env=env or ENV, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    PROCS.append(p)
    return p


def run(cmd: list[str], timeout: float = 60, env=None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=HERE, env=env or ENV, capture_output=True, text=True, timeout=timeout)


def rpc(url: str, body, headers=None) -> dict:
    data = body if isinstance(body, bytes) else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r)


class FakeServer(BaseHTTPRequestHandler):
    """/signin -> a GitHub-like HTML sign-in page; /401 -> 401 (private codespace port); /hang -> sleeps."""
    def log_message(self, *a):
        pass

    def _go(self):
        if self.path.startswith("/hang"):
            time.sleep(8)
        if self.path.startswith("/401"):
            self.send_response(401)
            self.end_headers()
            return
        body = b"<!DOCTYPE html><html><head><title>Sign in to GitHub</title></head><body>Sign in</body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    do_GET = do_POST = _go


SDK_CLIENT = r'''
import asyncio, sys
import httpx
from a2a.client import ClientConfig, create_client
from a2a.client.card_resolver import A2ACardResolver
from a2a.helpers import new_text_message
from a2a.types import Role, SendMessageRequest

async def main(url):
    async with httpx.AsyncClient() as http:        # the SDK's own card parser must accept our card
        card = await A2ACardResolver(http, url).get_agent_card()
    client = await create_client(card, client_config=ClientConfig(streaming=False))
    req = SendMessageRequest(message=new_text_message("interop hello", role=Role.ROLE_USER))
    out = []
    async for ev in client.send_message(req):
        if ev.HasField("message"):
            out += [p.text for p in ev.message.parts]
        elif ev.HasField("task"):
            out += [p.text for a in ev.task.artifacts for p in a.parts]
    print("CARD", card.name)
    print("REPLY", " ".join(out))
asyncio.run(main(sys.argv[1]))
'''

SDK_SERVER = r'''
import sys, uvicorn
from starlette.applications import Starlette
from a2a.server.agent_execution import AgentExecutor
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_jsonrpc_routes
from a2a.server.routes.agent_card_routes import create_agent_card_routes
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.helpers import new_task_from_user_message, new_text_part
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill

class Echo(AgentExecutor):          # the usual SDK pattern: a Task with an artifact, then COMPLETED
    async def execute(self, context, event_queue):
        task = context.current_task or new_task_from_user_message(context.message)
        await event_queue.enqueue_event(task)
        up = TaskUpdater(event_queue, task.id, task.context_id)
        await up.add_artifact([new_text_part("sdk-echo: " + context.get_user_input())], name="answer")
        await up.complete()
    async def cancel(self, context, event_queue):
        pass

port = int(sys.argv[1])
card = AgentCard(name="SDK Echo", description="official a2a-sdk server", version="1.0.0",
                 default_input_modes=["text/plain"], default_output_modes=["text/plain"],
                 capabilities=AgentCapabilities(streaming=False),
                 supported_interfaces=[AgentInterface(url=f"http://127.0.0.1:{port}/", protocol_binding="JSONRPC",
                                                      protocol_version="1.0")],
                 skills=[AgentSkill(id="echo", name="echo", description="echoes", tags=["test"])])
handler = DefaultRequestHandler(agent_executor=Echo(), task_store=InMemoryTaskStore(), agent_card=card)
app = Starlette(routes=[*create_agent_card_routes(card), *create_jsonrpc_routes(handler, "/")])
uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
'''


def sdk_python() -> str | None:
    cand = os.getenv("A2A_SDK_PYTHON")
    if cand:
        return cand
    try:
        import a2a.client  # noqa: F401
        return PY
    except ImportError:
        return None


def main() -> None:
    print(f"A2A Bazaar tests (mock mode) - {PY}\n")
    p1, p2, p3 = free_port(), free_port(), free_port()
    a1 = start([PY, "a2a_agent.py", "--persona", "pirate", "--port", str(p1)])
    a2 = start([PY, "a2a_agent.py", "--persona", "chef", "--port", str(p2)])
    start([PY, "a2a_agent.py", "--name", "Haiku", "--skill", "haiku", "--instructions", "Answer as a haiku.",
           "--port", str(p3)])
    ok = all(wait_port(p) for p in (p1, p2, p3))
    check("3 mock agents start (stdlib only, no key)", ok)
    if not ok:
        for p in PROCS:
            p.kill()
            print((p.stdout.read() if p.stdout else "")[-500:])
        sys.exit(1)
    u1 = f"http://127.0.0.1:{p1}"

    with urllib.request.urlopen(u1 + "/.well-known/agent-card.json", timeout=5) as r:
        card = json.load(r)
    itf = (card.get("supportedInterfaces") or [{}])[0]
    check("agent card at /.well-known/agent-card.json has A2A 1.0 fields",
          card.get("name") == "Pirate" and itf.get("protocolBinding") == "JSONRPC"
          and itf.get("protocolVersion") == "1.0" and itf.get("url", "").endswith(f":{p1}/")
          and card.get("skills") and card["capabilities"]["streaming"] is False, json.dumps(card)[:200])

    r = run([PY, "a2a_call.py", u1, "What is an API?"])
    check("a2a_call.py -> our agent: card + reply", r.returncode == 0 and "agent:  Pirate" in r.stdout
          and "[Pirate] [Pirate, mock]" in r.stdout and "What is an API?" in r.stdout, r.stdout + r.stderr)

    msg = {"messageId": "m1", "role": "ROLE_USER", "parts": [{"text": "hi"}], "contextId": "ctx-1"}
    good = rpc(u1 + "/", {"jsonrpc": "2.0", "id": 7, "method": "SendMessage", "params": {"message": msg}},
               {"A2A-Version": "1.0"})
    m = good.get("result", {}).get("message", {})
    check("SendMessage result shape: id echoed, ROLE_AGENT message with text part, contextId kept",
          good.get("id") == 7 and m.get("role") == "ROLE_AGENT" and m["parts"][0]["text"] and m.get("messageId")
          and m.get("contextId") == "ctx-1", json.dumps(good)[:200])
    errs = {
        -32700: rpc(u1 + "/", b"{not json"),
        -32600: rpc(u1 + "/", {"id": 1, "method": "SendMessage"}),
        -32601: rpc(u1 + "/", {"jsonrpc": "2.0", "id": 2, "method": "message/send", "params": {"message": msg}}),
        -32602: rpc(u1 + "/", {"jsonrpc": "2.0", "id": 3, "method": "SendMessage", "params": {}}),
        -32009: rpc(u1 + "/", {"jsonrpc": "2.0", "id": 4, "method": "SendMessage", "params": {"message": msg}},
                    {"A2A-Version": "0.3"}),
    }
    check("JSON-RPC errors: -32700 parse, -32600 request, -32601 method, -32602 params, -32009 version",
          all(v.get("error", {}).get("code") == k for k, v in errs.items()),
          json.dumps({k: v.get("error") for k, v in errs.items()})[:300])

    fake = ThreadingHTTPServer(("127.0.0.1", 0), FakeServer)
    threading.Thread(target=fake.serve_forever, daemon=True).start()
    fu = f"http://127.0.0.1:{fake.server_address[1]}"
    r = run([PY, "a2a_call.py", fu + "/signin", "hi"])
    check("a2a_call.py: HTML sign-in page -> 'port is not public' + fix", r.returncode != 0
          and "not public" in r.stderr and "Port Visibility -> Public" in r.stderr
          and "gh codespace ports visibility" in r.stderr and r.stderr.count("\n") <= 1, r.stderr)
    r = run([PY, "a2a_call.py", fu + "/401", "hi"])
    check("a2a_call.py: HTTP 401 -> 'port is not public'", r.returncode != 0 and "not public" in r.stderr, r.stderr)
    dead = f"http://127.0.0.1:{free_port()}"
    r = run([PY, "a2a_call.py", dead, "hi"])
    check("a2a_call.py: dead URL -> one-line 'connection refused'", r.returncode != 0
          and "connection refused" in r.stderr and r.stderr.count("\n") <= 1, r.stderr)

    urls = [u1, f"http://127.0.0.1:{p2}", f"http://127.0.0.1:{p3}", dead, fu + "/signin"]
    t0 = time.monotonic()
    r = run([PY, "bazaar.py", *urls, "--all", "--ask", "Plan an evening"], timeout=90)
    out = r.stdout
    check("bazaar.py --all: 3 answers side by side, dead + private agents shown as DOWN, run completes",
          r.returncode == 0 and "3 of 5 agents answer" in out and out.count("DOWN") == 2
          and all(n in out for n in ("Pirate (", "Chef (", "Haiku (")), out[-600:] + r.stderr[-300:])

    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write(f"# agents for the test\n{u1}\nChef: {urls[1]}/\n{urls[2]}/.well-known/agent-card.json\n{dead}\n")
    r = run([PY, "bazaar.py", "--file", f.name, "--ask", "Plan an evening"], timeout=90)
    check("bazaar.py default (mock orchestrator) from a URL file: answer names who said what",
          r.returncode == 0 and "3 of 4 agents answer" in r.stdout and "- Pirate said:" in r.stdout
          and "- Chef said:" in r.stdout and "- Haiku said:" in r.stdout, r.stdout[-600:] + r.stderr[-300:])
    os.unlink(f.name)

    # a hanging agent: its card answers, the message never does -> timeout, the run goes on
    hang_card = ThreadingHTTPServer(("127.0.0.1", 0), type("H", (BaseHTTPRequestHandler,), {
        "log_message": lambda *a: None,
        "do_GET": lambda s: (s.send_response(200), s.send_header("Content-Type", "application/json"), s.end_headers(),
                             s.wfile.write(json.dumps({"name": "Sleepy", "supportedInterfaces": [
                                 {"url": f"{fu}/hang", "protocolBinding": "JSONRPC", "protocolVersion": "1.0"}],
                                 "skills": []}).encode()))}))
    threading.Thread(target=hang_card.serve_forever, daemon=True).start()
    hu = f"http://127.0.0.1:{hang_card.server_address[1]}"
    t0 = time.monotonic()
    r = run([PY, "bazaar.py", u1, hu, "--all", "--timeout", "2", "--ask", "hi"], timeout=60)
    check("bazaar.py: a hanging agent times out, the others still answer",
          r.returncode == 0 and "timeout" in r.stdout and "[Pirate, mock]" in r.stdout and time.monotonic() - t0 < 20,
          r.stdout[-500:])

    sdk = sdk_python()
    if not sdk:
        print("SKIP  interop: official SDK client -> our server   (set A2A_SDK_PYTHON, see the docstring)")
        print("SKIP  interop: our client -> official SDK server")
    else:
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "sdk_client.py").write_text(SDK_CLIENT)
            (Path(td) / "sdk_server.py").write_text(SDK_SERVER)
            env = {k: v for k, v in ENV.items() if k != "A2A_MOCK"}
            r = subprocess.run([sdk, "-I", str(Path(td) / "sdk_client.py"), u1], capture_output=True, text=True,
                               timeout=60, env=env)
            check("interop: official a2a-sdk client -> our server (card + SendMessage)", r.returncode == 0
                  and "CARD Pirate" in r.stdout and "REPLY [Pirate, mock]" in r.stdout and "interop hello" in r.stdout,
                  (r.stdout + r.stderr)[-500:])
            ps = free_port()
            srv = start([sdk, "-I", str(Path(td) / "sdk_server.py"), str(ps)], env=env)
            if not wait_port(ps, 30):
                check("interop: our client -> official SDK server", False, "SDK server did not start")
            else:
                r = run([PY, "a2a_call.py", f"http://127.0.0.1:{ps}", "interop hello"])
                check("interop: our a2a_call.py -> official a2a-sdk server (Task + artifact reply)",
                      r.returncode == 0 and "agent:  SDK Echo" in r.stdout
                      and "[SDK Echo] sdk-echo: interop hello" in r.stdout, (r.stdout + r.stderr)[-500:])
            srv.kill()
        ver = subprocess.run([sdk, "-c", "import importlib.metadata as m; print(m.version('a2a-sdk'))"],
                             capture_output=True, text=True).stdout.strip()
        print(f"      (official SDK: a2a-sdk {ver})")

    for p in PROCS:
        p.kill()
    log = a1.stdout.read() if a1.stdout else ""
    check("agent logs one line per request", log.count("card") >= 2 and "\"What is an API?\"" in log, log[-400:])
    a2.kill()
    passed = sum(RESULTS)
    print(f"\n{passed}/{len(RESULTS)} passed")
    sys.exit(0 if passed == len(RESULTS) else 1)


if __name__ == "__main__":
    try:
        main()
    finally:
        for proc in PROCS:
            proc.kill()
