# /// script
# requires-python = ">=3.12"
# dependencies = ["genaiclass", "rich>=14.0"]
#
# [tool.uv.sources]
# genaiclass = { path = "../shared/python", editable = true }
# ///
"""The workshop runner - one entry point for every demo.

    uv run tools/workshop.py                 # interactive menu
    uv run tools/workshop.py --list          # just list what exists
    uv run tools/workshop.py --run 1.03      # run one demo by its number
    uv run tools/workshop.py --run 1.03 --profile mock
    uv run tools/workshop.py --segment 1     # run every demo in a segment
    uv run tools/workshop.py --code          # print each demo's source before running it (menu: c toggles)

Nobody has to write code or remember a path: pick a number, watch the output.
The runner reads the samples themselves - the title and the intro text come from
each file's first markdown cell, so a new sample shows up here automatically.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console, Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

ROOT = Path(__file__).resolve().parent.parent
SEGMENTS = {
    "01-foundations": "Segment 1 - Foundations & APIs",
    "02-integrating": "Segment 2 - Integrating (RAG, MCP)",
    "03-agents": "Segment 3 - Agents & orchestration",
    "04-local-media": "Segment 4 - Local models, images, video",
}
# Windows consoles still default to cp1252, which cannot encode the box-drawing
# characters rich uses - force UTF-8 before the first print, or the runner dies
# mid-demo with a UnicodeEncodeError.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

# legacy_windows=False: the old Windows console renderer crashes on styled output
# in Git Bash / conhost; forcing the ANSI path keeps the demo from dying on stage.
console = Console(legacy_windows=False)


# --------------------------------------------------------------------------- model


@dataclass
class Demo:
    number: str          # "1.03"
    segment: str         # "01-foundations"
    lang: str            # "python" | "csharp"
    path: Path           # file, or folder for hosted-agent demos
    title: str
    intro: str

    @property
    def label(self) -> str:
        return f"{self.title}  ({self.lang})"


def _read_header(path: Path) -> tuple[str, str]:
    """Title + intro from the file's first markdown cell ('# %% [markdown]')."""
    entry = path if path.is_file() else next(iter(sorted(path.glob("*.py"))), None)
    if entry is None:
        return path.name, ""
    text = entry.read_text(encoding="utf-8", errors="ignore")
    lines, title, intro = text.splitlines(), "", []
    in_md = False
    for line in lines:
        if line.strip().startswith(("# %% [markdown]", "// %% [markdown]")):
            in_md = True
            continue
        if in_md and line.strip().startswith(("# %%", "// %%")):
            break
        if in_md:
            body = re.sub(r"^\s*(#|//)\s?", "", line).rstrip()
            if body.startswith("# ") and not title:
                title = body[2:].strip()
            elif body.startswith("```"):       # skip the run instructions
                break
            elif body or intro:
                intro.append(body)
    intro_text = "\n".join(intro).strip()
    intro_text = re.split(r"\n\s*Run it:", intro_text)[0].strip()
    return title or entry.stem, intro_text


def discover() -> list[Demo]:
    demos: list[Demo] = []
    for seg_i, seg in enumerate(SEGMENTS, start=1):
        for lang, pattern in (("python", "*.py"), ("csharp", "*.cs")):
            folder = ROOT / "samples" / seg / lang
            if not folder.is_dir():
                continue
            entries = sorted(p for p in folder.iterdir()
                             if (p.is_file() and p.match(pattern)) or (p.is_dir() and not p.name.startswith(("_", "."))))
            for path in entries:
                m = re.match(r"(\d+)", path.name)
                if not m:
                    continue
                title, intro = _read_header(path)
                demos.append(Demo(f"{seg_i}.{m.group(1)}", seg, lang, path, title, intro))
    return demos


def profiles() -> dict[str, dict]:
    data = json.loads((ROOT / "providers.json").read_text(encoding="utf-8"))
    return data.get("profiles", data)


# --------------------------------------------------------------------------- view


def print_menu(demos: list[Demo], profile: str) -> None:
    console.print()
    console.print(Panel.fit(
        Text.from_markup(f"[bold]Building Stuff with GenAI[/bold] - workshop runner\n"
                         f"profile: [cyan]{profile}[/cyan]    "
                         f"[dim]number = run it  |  c = show code  |  p = profile  |  q = quit[/dim]"),
        border_style="cyan"))
    for seg, seg_title in SEGMENTS.items():
        rows = [d for d in demos if d.segment == seg]
        if not rows:
            continue
        table = Table(box=None, pad_edge=False, show_header=False, expand=True)
        table.add_column("n", style="bold cyan", width=6)
        table.add_column("title")
        table.add_column("lang", style="dim", width=7)
        seen: dict[str, Demo] = {}
        for d in rows:                       # python and C# twins share one line
            seen.setdefault(d.number, d)
        for num, d in seen.items():
            langs = "+".join(sorted({x.lang[:2] for x in rows if x.number == num}))
            table.add_row(num, d.title, langs)
        console.print()
        console.print(Rule(f"[bold]{seg_title}[/bold]", style="dim", align="left"))
        console.print(table)
    console.print()


def print_profiles(profs: dict[str, dict], current: str) -> None:
    table = Table(title="profiles (providers.json)", box=None, title_justify="left")
    table.add_column("key", style="bold cyan")
    table.add_column("label")
    table.add_column("model", style="dim")
    for key, p in profs.items():
        mark = " [green]<- current[/green]" if key == current else ""
        table.add_row(key, (p.get("label", "") + mark), str(p.get("model", "")))
    console.print(table)


# --------------------------------------------------------------------------- run


AGENT_URL = "http://localhost:8088"
CLIENT_14 = ROOT / "samples" / "03-agents" / "python" / "14_call_hosted_agent.py"
SERVER_12 = ROOT / "samples" / "03-agents" / "python" / "12_foundry_hosted_maf"


def command_for(demo: Demo, profile: str) -> list[str]:
    if demo.lang == "python":
        target = demo.path if demo.path.is_file() else demo.path / "main.py"
        return ["uv", "run", str(target), "--profile", profile]
    if demo.path.is_dir():                 # 12_foundry_hosted_maf is a real project (container build)
        return ["dotnet", "run", "--project", str(demo.path)]
    return ["dotnet", "run", str(demo.path), "--", "--profile", profile]


def is_agent_server(demo: Demo) -> bool:
    """Hosted-agent folders (12, 13) are servers that never exit on their own."""
    return demo.path.is_dir() and demo.segment == "03-agents"


def profile_env(profile: str) -> dict[str, str]:
    """GENAI_* for programs that read variables instead of --profile (the C# hosted agent)."""
    try:
        from genaiclass import get_profile
        p = get_profile(profile)
        return {"GENAI_BASE_URL": p.base_url, "GENAI_API_KEY": p.api_key or "none", "GENAI_MODEL": p.model}
    except Exception:
        return {}


def run_with_agent_server(server_cmd: list[str], env: dict, cwd: Path) -> int:
    """Start a hosted agent locally, wait for /readiness, call it with sample 14, stop it.

    This is the whole Foundry hosted-agent story on a laptop: the same container code, the
    same Responses protocol on :8088 - only `azd deploy` is missing."""
    import urllib.request
    console.print(Text("starting the agent server: " + " ".join(server_cmd), style="dim"))
    server = subprocess.Popen(server_cmd, cwd=cwd, env=env)
    try:
        for _ in range(180):                          # first run builds/installs: up to 3 minutes
            if server.poll() is not None:
                console.print(f"[red]agent server exited early (code {server.returncode})[/red]")
                return server.returncode or 1
            try:
                urllib.request.urlopen(AGENT_URL + "/readiness", timeout=2)
                break
            except Exception:
                time.sleep(1)
        else:
            console.print("[red]agent server did not become ready in 180 s[/red]")
            return 1
        console.print(Rule("[dim]agent is up on :8088 - calling it like any Responses endpoint (sample 14)[/dim]",
                           style="dim"))
        return subprocess.run(["uv", "run", str(CLIENT_14), "--url", AGENT_URL], cwd=ROOT, env=env).returncode
    finally:
        # `uv run` / `dotnet run` start the real server as a CHILD process. terminate() only
        # ends the launcher, the orphaned server keeps :8088 and the terminal busy - kill the tree.
        if os.name == "nt":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(server.pid)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            server.terminate()
        try:
            server.wait(10)
        except subprocess.TimeoutExpired:
            server.kill()


def show_code(demo: Demo) -> None:
    """The source the audience is about to see run, without the markdown cells (the intro panel has them)."""
    entry = demo.path if demo.path.is_file() else next(iter(sorted(demo.path.glob("*.py" if demo.lang == "python" else "*.cs"))), None)
    if entry is None:
        return
    lines, keep, in_md = entry.read_text(encoding="utf-8").splitlines(), [], False
    for line in lines:
        if line.strip().startswith(("# %% [markdown]", "// %% [markdown]")):
            in_md = True
            continue
        if line.strip().startswith(("# %%", "// %%")):
            in_md = False
        if not in_md:
            keep.append(line)
    code = "\n".join(keep).strip()
    console.print(Panel(Syntax(code, "python" if demo.lang == "python" else "csharp", theme="monokai",
                               line_numbers=True, word_wrap=True),
                        title=str(entry.relative_to(ROOT)), title_align="left", border_style="dim"))


def run(demo: Demo, profile: str, code: bool = False) -> int:
    console.print()
    console.print(Rule(f"[bold cyan]{demo.number}  {demo.title}[/bold cyan]", style="cyan"))
    if demo.intro:
        console.print(Panel(Markdown(demo.intro), border_style="dim", title="what this shows",
                            title_align="left"))
    if code:
        show_code(demo)
    cmd = command_for(demo, profile)
    console.print(Text(" ".join(cmd), style="dim"))
    console.print(Rule(style="dim"))
    t0 = time.time()
    try:
        # children inherit cp1252 on Windows and die on the first non-ASCII print (a ✓ killed 2.05)
        env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
        if is_agent_server(demo):
            # 12/13 are servers: run them, call them with 14, stop them
            code = run_with_agent_server(cmd, {**env, **profile_env(profile)}, ROOT)
        elif demo.path == CLIENT_14:
            # 14 alone needs something to call: bring up the MAF agent from 12 first
            code = run_with_agent_server(["uv", "run", str(SERVER_12 / "main.py"), "--profile", profile],
                                         {**env, **profile_env(profile)}, ROOT)
        else:
            code = subprocess.run(cmd, cwd=ROOT, env=env).returncode
    except KeyboardInterrupt:
        console.print("\n[yellow]interrupted[/yellow]")
        return 130
    except FileNotFoundError as e:
        console.print(f"[red]cannot run:[/red] {e}")
        return 127
    dt = time.time() - t0
    style, word = ("green", "done") if code == 0 else ("red", f"exit {code}")
    console.print(Rule(f"[{style}]{word}[/{style}] [dim]in {dt:.1f}s[/dim]", style=style))
    return code


def interactive(demos: list[Demo], profile: str, code: bool = False) -> None:
    profs = profiles()
    while True:
        print_menu(demos, profile)
        try:
            choice = console.input("[bold cyan]> [/bold cyan]").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return
        if choice in {"q", "quit", "exit"}:
            return
        if choice in {"c", "code"}:
            code = not code
            console.print(f"[dim]show code before running: {'on' if code else 'off'}[/dim]")
            continue
        if choice in {"p", "profile"}:
            print_profiles(profs, profile)
            pick = console.input("profile key (enter to keep): ").strip()
            if pick in profs:
                profile = pick
            continue
        matches = [d for d in demos if d.number == choice]
        if not matches:
            console.print("[yellow]no such number[/yellow]")
            continue
        demo = matches[0]
        if len(matches) > 1:                   # python + C# twin: ask which
            console.print(f"[dim]{choice} exists as: " + ", ".join(d.lang for d in matches) + "[/dim]")
            lang = console.input("language [python]: ").strip() or "python"
            demo = next((d for d in matches if d.lang == lang), matches[0])
        run(demo, profile, code)
        console.input("\n[dim]enter to return to the menu[/dim] ")


# --------------------------------------------------------------------------- main


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the workshop demos.")
    ap.add_argument("--list", action="store_true", help="list demos and exit")
    ap.add_argument("--run", metavar="N", help="run one demo by number, e.g. 1.03")
    ap.add_argument("--segment", metavar="S", help="run every demo in a segment, e.g. 1")
    ap.add_argument("--lang", default="python", choices=["python", "csharp"])
    ap.add_argument("--profile", default=None, help="provider profile (default: GENAI_PROFILE)")
    ap.add_argument("--code", action="store_true", help="print each demo's source before running it")
    args = ap.parse_args()

    demos = discover()
    profile = args.profile
    if profile is None:
        # GENAI_PROFILE from .env decides; say so loudly if it cannot be read instead of silently demoing
        # the mock (a swallowed AttributeError did exactly that on 2026-09-23).
        try:
            from genaiclass import get_profile
            profile = get_profile().name
        except Exception as e:
            profile = "mock"
            console.print(f"[yellow]could not resolve GENAI_PROFILE ({e}); using mock[/yellow]")

    if args.list:
        for d in demos:
            console.print(f"[cyan]{d.number}[/cyan] {d.label}")
        return 0
    if args.run:
        picks = [d for d in demos if d.number == args.run and d.lang == args.lang]
        if not picks:
            console.print(f"[red]no demo {args.run} ({args.lang})[/red]")
            return 2
        return run(picks[0], profile, args.code)
    if args.segment:
        picks = [d for d in demos if d.number.startswith(f"{args.segment}.") and d.lang == args.lang]
        bad = [d.number for d in picks if run(d, profile, args.code) != 0]
        console.print()
        console.print(Panel.fit(f"{len(picks) - len(bad)}/{len(picks)} ok"
                                + (f"  failed: {', '.join(bad)}" if bad else ""),
                                border_style="red" if bad else "green"))
        return 1 if bad else 0

    interactive(demos, profile, args.code)
    return 0


if __name__ == "__main__":
    sys.exit(main())
