# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Run every sample against the offline mock and report PASS/FAIL.

    uv run tools/smoke_test.py                 # everything
    uv run tools/smoke_test.py 03-agents       # only paths containing this text

Starts the mock server if nothing answers on :8080. Hosted agents are started as
servers, called with `14_call_hosted_agent.py`, then stopped. Nothing needs a key
or network access beyond package downloads - this is the "does it still run the
week before the workshop" check.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SAMPLES = REPO / "samples"
ENV = {**os.environ, "GENAI_NO_BROWSER": "1", "PYTHONIOENCODING": "utf-8"}
TIMEOUT = 600


def reachable(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            return response.status < 500
    except Exception:
        return False


def wait_for(url: str, seconds: int) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if reachable(url):
            return True
        time.sleep(1)
    return False


def run(command: list[str], cwd: Path) -> tuple[bool, str]:
    try:
        done = subprocess.run(command, cwd=cwd, env=ENV, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return False, "timeout"
    tail = [line for line in (done.stdout + done.stderr).splitlines()
            if line.strip() and not line.startswith("warning")][-1:]
    return done.returncode == 0, (tail[0][:100] if tail else "")


def stop(process: subprocess.Popen) -> None:
    if os.name == "nt":  # uv/dotnet spawn children; kill the whole tree
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True)
    else:
        process.terminate()
    process.wait(timeout=30)


def scripts() -> list[Path]:
    found = []
    for path in sorted(SAMPLES.rglob("*")):
        if any(part in {"bin", "obj", "node_modules"} for part in path.parts):
            continue
        if path.suffix == ".py" and path.name != "main.py":
            found.append(path)
        elif path.suffix == ".cs" and path.name != "Program.cs":
            found.append(path)
    return found


def hosted() -> list[tuple[str, list[str], Path]]:
    agents = SAMPLES / "03-agents"
    return [
        ("python/12_foundry_hosted_maf", ["uv", "run", "--no-progress", "main.py", "--profile", "mock"],
         agents / "python" / "12_foundry_hosted_maf"),
        ("python/13_foundry_hosted_langgraph", ["uv", "run", "--no-progress", "main.py", "--profile", "mock"],
         agents / "python" / "13_foundry_hosted_langgraph"),
        ("csharp/12_foundry_hosted_maf", ["dotnet", "run"],
         agents / "csharp" / "12_foundry_hosted_maf"),
    ]


def main(argv: list[str]) -> int:
    only = argv[0] if argv else ""
    mock = None
    if not reachable("http://localhost:8080/v1/models"):
        mock = subprocess.Popen(["uv", "run", "--no-progress", str(REPO / "tools" / "mock_server.py")],
                                cwd=REPO, env=ENV, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not wait_for("http://localhost:8080/v1/models", 60):
            print("mock server did not start")
            return 1

    results: list[tuple[str, bool, str]] = []
    try:
        for script in scripts():
            label = str(script.relative_to(SAMPLES)).replace("\\", "/")
            if only not in label or label.endswith("14_call_hosted_agent.py"):
                continue
            if script.suffix == ".py":
                ok, note = run(["uv", "run", "--no-progress", script.name, "--profile", "mock"], script.parent)
            else:
                ok, note = run(["dotnet", "run", script.name, "--", "--profile", "mock"], script.parent)
            results.append((label, ok, note))
            print(f"{'PASS' if ok else 'FAIL'}  {label}")

        client = SAMPLES / "03-agents" / "python"
        for label, command, cwd in hosted():
            label = f"03-agents/{label} (+14 client)"
            if only not in label:
                continue
            server = subprocess.Popen(command, cwd=cwd, env=ENV,
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                if not wait_for("http://localhost:8088/readiness", 240):
                    results.append((label, False, "server never became ready"))
                else:
                    ok, note = run(["uv", "run", "--no-progress", "14_call_hosted_agent.py"], client)
                    results.append((label, ok, note))
            finally:
                stop(server)
                time.sleep(2)
            print(f"{'PASS' if results[-1][1] else 'FAIL'}  {label}")
    finally:
        if mock:
            stop(mock)

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed")
    for label, _, note in failed:
        print(f"  FAIL {label}: {note}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
