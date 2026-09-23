#!/usr/bin/env python3
"""test_labs.py - run every lab solution (or starter) against the endpoint configured in labs/.env / the environment.

    python labs/_tools/test_labs.py                      # all labs, all languages found on this machine
    python labs/_tools/test_labs.py --lab 01 --lang python
    python labs/_tools/test_labs.py --starters           # starters must stop at a TODO, not crash earlier

Skips files whose name contains "_server" (they are started by the client scripts) and files listed in SKIP.
Logs go to labs/_tools/test_logs/. Needs: python (this interpreter), `dotnet` for C#, `node` for TypeScript.
"""
import argparse
import os
import re
import shutil
import urllib.request
import subprocess
import sys
import time
from pathlib import Path

LABS = Path(__file__).resolve().parent.parent
LOGS = Path(__file__).resolve().parent / "test_logs"
RUNNERS = {".py": [sys.executable], ".cs": ["dotnet", "run", "--file"], ".mjs": ["node"]}
LANG_OF = {".py": "python", ".cs": "csharp", ".mjs": "typescript"}
SKIP = {"interactive", "devui"}   # substrings of file names that are never run automatically (servers/UIs)
_REAL_WF = LABS / "04-local-media" / "comfyui_workflows" / "01_txt2img_sdxl.json"   # the talk's workflow, if present
FIXTURE = str(_REAL_WF if _REAL_WF.exists() else Path(__file__).resolve().parent / "fixtures" / "txt2img_api.json")
OUT = str(Path(__file__).resolve().parent / "test_logs" / "out")
ARGS = {  # scripts that need command-line arguments (Lab 4 ComfyUI steps run against _tools/comfy_mock.py or a real ComfyUI)
    "02_comfy_run.py": [FIXTURE, "--prompt", "a lighthouse in fog", "--seed", "42", "--out", OUT],
    "03_one_knob.py": [FIXTURE, "--knob", "cfg", "--values", "2", "6", "--seed", "42", "--prompt", "a lighthouse", "--out", OUT],
}
# a starter "stops at a TODO" when an exception line carries the TODO placeholder text - also when a runtime wraps it
# (C# MAF workflows: "InvalidOperationException: workflow failed: TODO 2: ...")
TODO_STOP = re.compile(r"(Error|Exception)\b[^\n]*?:\s*'?TODO \d")


def comfy_up() -> bool:
    try:
        urllib.request.urlopen(os.getenv("COMFYUI_URL", "http://127.0.0.1:8188").rstrip("/") + "/system_stats", timeout=3)
        return True
    except Exception:
        return False


def discover(lab: str | None, lang: str | None, starters: bool):
    for f in sorted(LABS.glob("[0-9][0-9]-*/*/**/*")):
        if not f.is_file() or f.suffix not in RUNNERS or "node_modules" in f.parts or "data" in f.parts:
            continue
        if ("solution" in f.parts) == starters:
            continue
        if lab and not f.relative_to(LABS).parts[0].startswith(lab):
            continue
        if lang and LANG_OF[f.suffix] != lang:
            continue
        if "_server" in f.stem or any(s in f.stem for s in SKIP) or f.parent.name == "_shared":
            continue
        yield f


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lab"); ap.add_argument("--lang"); ap.add_argument("--starters", action="store_true")
    ap.add_argument("--timeout", type=int, default=int(os.getenv("GENAI_TEST_TIMEOUT", "600")))
    a = ap.parse_args()
    LOGS.mkdir(exist_ok=True)
    results = []
    for f in discover(a.lab, a.lang, a.starters):
        cmd = RUNNERS[f.suffix]
        if not shutil.which(cmd[0]):
            results.append((f, "SKIP (no " + cmd[0] + ")", 0.0)); continue
        if f.name in ARGS and not comfy_up():
            results.append((f, "SKIP (no ComfyUI)", 0.0)); print(f"{'SKIP (no ComfyUI)':<22}         {f.relative_to(LABS)}"); continue
        t0 = time.perf_counter()
        try:
            p = subprocess.run(cmd + [f.name] + ARGS.get(f.name, []), cwd=f.parent, capture_output=True, text=True, timeout=a.timeout)
            out, code = p.stdout + p.stderr, p.returncode
        except subprocess.TimeoutExpired as e:
            out, code = f"TIMEOUT after {a.timeout}s\n{e.stdout or ''}{e.stderr or ''}", -1
        dt = time.perf_counter() - t0
        rel = f.relative_to(LABS)
        (LOGS / (str(rel).replace(os.sep, "__") + ".log")).write_text(out if isinstance(out, str) else str(out), encoding="utf-8")
        if a.starters:
            # a starter passes if it runs to the end (no TODO in it) or stops exactly at a TODO placeholder
            status = "PASS (runs)" if code == 0 else ("PASS (stops at TODO)" if TODO_STOP.search(out) else f"FAIL (exit {code})")
        else:
            status = "PASS" if code == 0 else f"FAIL (exit {code})"
        results.append((f, status, dt))
        print(f"{status:<22} {dt:6.1f}s  {rel}", flush=True)
    failed = [r for r in results if r[1].startswith("FAIL")]
    print(f"\n{len(results)} run, {len(failed)} failed, {sum(1 for r in results if r[1].startswith('SKIP'))} skipped; logs in {LOGS}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
