# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Does this machine have what the labs need?

    uv run tools/check_env.py

Checks toolchains, then tries a real one-token call against every configured
provider profile. Exits non-zero if nothing at all can be reached, so it can
also run in CI.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OK, WARN, FAIL = "[ ok ]", "[warn]", "[fail]"


def version_of(executable: str, *args: str) -> str | None:
    if shutil.which(executable) is None:
        return None
    try:
        result = subprocess.run([executable, *args], capture_output=True, text=True, timeout=60)
        return (result.stdout or result.stderr).strip().splitlines()[0]
    except Exception:
        return None


def check_tools() -> list[str]:
    problems = []
    print("Toolchains")
    for label, executable, args, required, hint in [
        ("uv", "uv", ("--version",), True, "https://docs.astral.sh/uv/"),
        (".NET SDK", "dotnet", ("--version",), False, "needs 10.x for the C# track"),
        ("Node", "node", ("--version",), False, "20+ for the TypeScript track"),
        ("Docker", "docker", ("--version",), False, "only for pgvector in Segment 2"),
        ("Ollama", "ollama", ("--version",), False, "only for the local track"),
    ]:
        found = version_of(executable, *args)
        if found:
            print(f"  {OK} {label:<10} {found}")
            if label == ".NET SDK" and not found.startswith("10."):
                print(f"       {WARN} file-based apps need .NET 10; found {found}")
        elif required:
            print(f"  {FAIL} {label:<10} missing - {hint}")
            problems.append(label)
        else:
            print(f"  {WARN} {label:<10} missing - {hint}")
    return problems


def expand(value: str) -> str:
    def sub(match: re.Match[str]) -> str:
        return os.environ.get(match.group(1)) or (match.group(2) or "")
    return re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}", sub, value)


def load_dotenv() -> None:
    path = REPO / ".env"
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"'))


def check_profiles() -> int:
    load_dotenv()
    config = json.loads((REPO / "providers.json").read_text(encoding="utf-8"))
    print("\nProvider profiles")
    reachable = 0

    for name, entry in config["profiles"].items():
        base_url = expand(entry["base_url"]).rstrip("/")
        api_key = expand(entry["api_key"])
        model = expand(entry.get("model", ""))

        if not base_url or "<" in base_url or not api_key:
            print(f"  {WARN} {name:<14} not configured")
            continue

        body = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": "ping"}],
            "max_completion_tokens": 1,
        }).encode()
        headers = {"Content-Type": "application/json"}
        if entry.get("key_header", "authorization").lower() == "api-key":
            headers["api-key"] = api_key
        else:
            headers["Authorization"] = f"Bearer {api_key}"

        request = urllib.request.Request(f"{base_url}/chat/completions", body, headers)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                response.read()
            print(f"  {OK} {name:<14} {model} reachable")
            reachable += 1
        except urllib.error.HTTPError as error:
            # 400 still proves the endpoint and key are live.
            verdict = OK if error.code == 400 else FAIL
            print(f"  {verdict} {name:<14} HTTP {error.code} {error.reason}")
            reachable += verdict == OK
        except Exception as error:
            print(f"  {FAIL} {name:<14} {type(error).__name__}")

    return reachable


def main() -> int:
    print(f"genaiclass environment check  ({sys.platform}, python {sys.version.split()[0]})\n")
    problems = check_tools()
    reachable = check_profiles()

    print()
    if problems:
        print(f"{FAIL} missing required tooling: {', '.join(problems)}")
        return 1
    if reachable == 0:
        print(f"{WARN} no provider reachable. Start the offline stub and re-run:")
        print("      uv run tools/mock_server.py")
        return 1
    print(f"{OK} {reachable} provider profile(s) reachable - you are ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
