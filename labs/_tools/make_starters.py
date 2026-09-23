#!/usr/bin/env python3
"""make_starters.py - generate the attendee starter files from the solutions (single source of truth).

Solutions live in labs/<lab>/<lang>/solution/. A starter is the same file with every block between
    # >>> TODO n: hint          (// >>> TODO n: hint  in C# / JavaScript)
    ...solution code...
    # <<< TODO
replaced by the hint and a placeholder that fails loudly (raise NotImplementedError / throw ...).
Files without TODO blocks are copied unchanged, so every step stays runnable.

    python labs/_tools/make_starters.py            # (re)generate all starters
    python labs/_tools/make_starters.py --check    # exit 1 if a starter is out of date (CI / before the day)
"""
import re
import sys
from pathlib import Path

LABS = Path(__file__).resolve().parent.parent
STYLE = {
    ".py": ("#", 'raise NotImplementedError("{hint}")'),
    ".cs": ("//", 'throw new NotImplementedException("{hint}");'),
    ".mjs": ("//", 'throw new Error("{hint}");'),
    ".js": ("//", 'throw new Error("{hint}");'),
    ".ts": ("//", 'throw new Error("{hint}");'),
}
BANNER = "STARTER - complete the TODO block(s). The finished version is in solution/{name}"


def make_starter(src: Path) -> str:
    comment, placeholder = STYLE[src.suffix]
    start = re.compile(rf"^(\s*){re.escape(comment)} >>> (TODO.*)$")
    end = re.compile(rf"^\s*{re.escape(comment)} <<< TODO\s*$")
    out, inside, found = [], False, False
    for line in src.read_text(encoding="utf-8").splitlines():
        m = start.match(line)
        if m:
            indent, hint = m.group(1), m.group(2).replace('"', "'")
            out += [f"{indent}{comment} {hint}", indent + placeholder.format(hint=hint)]
            inside, found = True, True
        elif end.match(line):
            inside = False
        elif not inside:
            out.append(line)
    if inside:
        raise SystemExit(f"{src}: unterminated TODO block")
    if found:  # banner after shebang / #: directives (C# file-based apps need those first)
        idx = 0
        while idx < len(out) and (out[idx].startswith("#!") or out[idx].startswith("#:")):
            idx += 1
        out.insert(idx, f"{comment} {BANNER.format(name=src.name)}")
    return "\n".join(out) + "\n"


def main() -> int:
    check, stale = "--check" in sys.argv, []
    for src in sorted(LABS.glob("*/*/solution/**/*")):
        if not src.is_file() or src.suffix not in STYLE:
            continue
        rel = src.relative_to(LABS)
        parts = list(rel.parts)
        parts.remove("solution")
        dst = LABS.joinpath(*parts)
        text = make_starter(src)
        if dst.exists() and dst.read_text(encoding="utf-8") == text:
            continue
        stale.append(str(dst.relative_to(LABS)))
        if not check:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(text, encoding="utf-8")
    verb = "out of date" if check else "written"
    print(f"{len(stale)} starter(s) {verb}" + ("".join(f"\n  {s}" for s in stale) if stale else ""))
    return 1 if (check and stale) else 0


if __name__ == "__main__":
    sys.exit(main())
