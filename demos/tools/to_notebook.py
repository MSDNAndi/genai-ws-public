# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Generate notebooks from the sample scripts.

The scripts are the single source of truth. They are marked up in the widely
used "percent" format - `# %%` starts a code cell, `# %% [markdown]` a prose
cell - which means the same file runs as a plain script *and* converts to a
notebook. Edit the script; regenerate the notebook.

    uv run tools/to_notebook.py                    # everything under samples/
    uv run tools/to_notebook.py samples/01-foundations/python/04_tool_calling.py

Output lands in notebooks/<segment>/<language>/ as:
  * `.ipynb` - open in Verso, ClrKernel, JupyterLab
  * `.dib`   - Verso / Polyglot plain-text format, diffs like source (C# only)

C# notebooks cannot reference a .csproj, so `#:project ...` is rewritten into
`#r "nuget: ..."` lines taken from that project plus an `#r` to its built
assembly. Build the shared project once before using them:

    dotnet build shared/csharp/GenAIClass/GenAIClass.csproj
"""

from __future__ import annotations

import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "notebooks"

LANGUAGES = {
    ".py": {"marker": "# %%", "comment": "# ", "kernel": "python3",
            "display": "Python 3", "language": "python"},
    ".cs": {"marker": "// %%", "comment": "// ", "kernel": "csharp",
            "display": "C#", "language": "csharp"},
}
# C# samples are NOT converted by default (2026-09-23). The only C# notebook kernel, .NET Interactive
# (archived 2026-04), runs on .NET 9; the samples are .NET 10 apps on OpenAI 2.14 + GenAIClass.dll
# (net10.0), which a net9 kernel cannot load - every generated C# notebook failed on its first cell.
# Show C# with `uv run tools/workshop.py --lang csharp --code`, or see classic/csharp/ for notebooks
# rebuilt to run on net9. Pass a .cs path explicitly to convert one anyway.
DEFAULT_SUFFIXES = {".py"}


def split_cells(text: str, spec: dict) -> list[tuple[str, str]]:
    """Split percent-format source into (kind, source) cells."""
    marker, comment = spec["marker"], spec["comment"]
    cells: list[tuple[str, str]] = []
    kind, buffer = "code", []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(marker):
            if buffer:
                cells.append((kind, "\n".join(buffer).strip("\n")))
                buffer = []
            kind = "markdown" if "[markdown]" in stripped else "code"
            continue
        if kind == "markdown":
            # Strip the leading comment marker from prose lines.
            if stripped.startswith(comment.strip()):
                line = line.lstrip()[len(comment.strip()):]
                buffer.append(line[1:] if line.startswith(" ") else line)
            elif not stripped:
                buffer.append("")
            continue
        buffer.append(line)

    if buffer:
        cells.append((kind, "\n".join(buffer).strip("\n")))
    return [(kind, source) for kind, source in cells if source.strip()]


def project_directives(csproj: Path, out_dir: Path) -> list[str]:
    """`#r` lines that stand in for a project reference inside a notebook."""
    if not csproj.is_file():
        return [f'// project not found: {csproj}']
    root = ET.parse(csproj).getroot()
    lines = []
    for reference in root.iter("PackageReference"):
        name, version = reference.get("Include"), reference.get("Version")
        if name and version:
            lines.append(f'#r "nuget: {name}, {version}"')
    target = (root.findtext(".//TargetFramework") or "net10.0").strip()
    dll = csproj.parent / "bin" / "Debug" / target / f"{csproj.stem}.dll"
    relative = Path(os.path.relpath(dll, out_dir)).as_posix()
    lines.append(f'#r "{relative}"')
    return lines


def rewrite_header(source: str, script: Path, out_dir: Path) -> str:
    """Turn script-only headers into notebook-only headers."""
    lines_out: list[str] = []
    for line in source.splitlines():
        match = re.match(r"^#:project\s+(\S+)", line.strip())
        if match:
            lines_out.extend(project_directives((script.parent / match.group(1)).resolve(), out_dir))
            continue
        if line.strip().startswith("#:"):  # #:property, #:sdk - build-time only
            continue
        lines_out.append(line)
    joined = "\n".join(lines_out)
    # A notebook cell has no `args`; the profile then comes from GENAI_PROFILE.
    return joined.replace("Providers.GetProfile(args: args)", "Providers.GetProfile()")


def strip_inline_metadata(source: str) -> str:
    """Drop the PEP 723 block - a notebook resolves packages differently."""
    return re.sub(r"^# /// script.*?^# ///\n", "", source, flags=re.S | re.M)


def to_ipynb(cells: list[tuple[str, str]], spec: dict) -> dict:
    return {
        "cells": [
            {"cell_type": kind, "metadata": {}, "source": source.splitlines(keepends=True),
             **({} if kind == "markdown" else {"execution_count": None, "outputs": []})}
            for kind, source in cells
        ],
        "metadata": {
            "kernelspec": {"name": spec["kernel"], "display_name": spec["display"],
                           "language": spec["language"]},
            "language_info": {"name": spec["language"]},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def to_dib(cells: list[tuple[str, str]], spec: dict) -> str:
    parts = ["#!meta\n\n" + json.dumps(
        {"kernelInfo": {"defaultKernelName": spec["kernel"],
                        "items": [{"name": spec["kernel"], "languageName": spec["language"]}]}},
        indent=2)]
    for kind, source in cells:
        parts.append(f"#!{'markdown' if kind == 'markdown' else spec['kernel']}\n\n{source}")
    return "\n\n".join(parts) + "\n"


def convert(script: Path) -> list[Path]:
    spec = LANGUAGES.get(script.suffix)
    if spec is None:
        return []

    source = script.read_text(encoding="utf-8")
    relative = script.relative_to(REPO / "samples")
    destination = OUT / relative.parent
    destination.mkdir(parents=True, exist_ok=True)

    source = strip_inline_metadata(source)
    source = rewrite_header(source, script, destination)
    cells = split_cells(source, spec)
    if not cells:
        return []

    written = [destination / f"{script.stem}.ipynb"]
    written[0].write_text(json.dumps(to_ipynb(cells, spec), indent=1), encoding="utf-8")
    if script.suffix == ".cs":
        dib = destination / f"{script.stem}.dib"
        dib.write_text(to_dib(cells, spec), encoding="utf-8")
        written.append(dib)
    return written


def main(argv: list[str]) -> int:
    targets = [Path(a).resolve() for a in argv] or sorted(
        p for p in (REPO / "samples").rglob("*")
        if p.suffix in DEFAULT_SUFFIXES
        and not {"bin", "obj", "node_modules"} & set(p.parts)  # build output, not samples
        and LANGUAGES[p.suffix]["marker"] in p.read_text(encoding="utf-8", errors="ignore")
    )
    count = 0
    for script in targets:
        for written in convert(script):
            print(f"  {written.relative_to(REPO)}")
            count += 1
    print(f"{count} notebook file(s) written to {OUT.relative_to(REPO)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
