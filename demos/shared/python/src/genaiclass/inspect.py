"""Drill into response objects.

Polyglot Notebooks gave you a rich, expandable view of whatever a cell returned,
and poking at a `ChatCompletion` was half the lesson. Nothing about that view was
magic: it walked the object and rendered a tree. These helpers do the same thing
from a plain script.

* `dump(obj)`        - a tree in the terminal, types included
* `inspect(obj)`     - a collapsible HTML page, opened in your browser
* `raw_json(response)` - the untouched HTTP body, before any SDK typing
"""

from __future__ import annotations

import dataclasses
import html
import json
import os
import tempfile
import webbrowser
from datetime import date, datetime
from pathlib import Path
from typing import Any

_PRIMITIVES = (str, int, float, bool, type(None))


def to_plain(obj: Any, _depth: int = 0, _max_depth: int = 12) -> Any:
    """Turn any SDK object into dicts/lists/primitives, keeping the shape."""
    if _depth > _max_depth:
        return f"<max depth reached: {type(obj).__name__}>"
    if isinstance(obj, _PRIMITIVES):
        return obj
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, (list, tuple, set)):
        return [to_plain(item, _depth + 1, _max_depth) for item in obj]
    if isinstance(obj, dict):
        return {str(k): to_plain(v, _depth + 1, _max_depth) for k, v in obj.items()}
    if hasattr(obj, "model_dump"):  # pydantic - every OpenAI SDK model
        try:
            return to_plain(obj.model_dump(exclude_none=False), _depth + 1, _max_depth)
        except Exception:
            pass
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return to_plain(dataclasses.asdict(obj), _depth + 1, _max_depth)
    if hasattr(obj, "__dict__"):
        return {k: to_plain(v, _depth + 1, _max_depth)
                for k, v in vars(obj).items() if not k.startswith("_")}
    return repr(obj)


def _type_label(value: Any) -> str:
    if isinstance(value, dict):
        return f"object ({len(value)} fields)"
    if isinstance(value, list):
        return f"array ({len(value)} items)"
    return type(value).__name__


def dump(obj: Any, title: str | None = None, max_depth: int = 12) -> None:
    """Print an object as an indented tree - the terminal version of the notebook view."""
    plain = to_plain(obj, _max_depth=max_depth)
    print(f"\n{title or type(obj).__name__}  [{_type_label(plain)}]")

    def walk(node: Any, prefix: str = "") -> None:
        if isinstance(node, dict):
            items = list(node.items())
        elif isinstance(node, list):
            items = [(f"[{i}]", v) for i, v in enumerate(node)]
        else:
            return
        for index, (key, value) in enumerate(items):
            last = index == len(items) - 1
            branch = "`- " if last else "|- "
            if isinstance(value, (dict, list)):
                print(f"{prefix}{branch}{key}  <{_type_label(value)}>")
                walk(value, prefix + ("   " if last else "|  "))
            else:
                shown = repr(value)
                if len(shown) > 120:
                    shown = shown[:117] + "..."
                print(f"{prefix}{branch}{key} = {shown}")

    walk(plain)
    print()


def raw_json(response: Any) -> str:
    """The untouched HTTP body.

    Every OpenAI SDK method has a `.with_raw_response` variant; this also accepts
    whatever that returns, so you can show students the wire format next to the
    typed object:

        raw = client.chat.completions.with_raw_response.create(...)
        print(raw_json(raw))
        completion = raw.parse()
    """
    for attribute in ("http_response", "response"):
        inner = getattr(response, attribute, None)
        if inner is not None and hasattr(inner, "text"):
            try:
                return json.dumps(json.loads(inner.text), indent=2)
            except Exception:
                return inner.text
    return json.dumps(to_plain(response), indent=2, default=str)


_HTML_HEAD = """<!doctype html><meta charset="utf-8"><title>{title}</title>
<style>
 :root {{ color-scheme: light dark; }}
 body {{ font: 13px/1.5 ui-monospace, Consolas, monospace; margin: 1.5rem; }}
 h1 {{ font-size: 1.1rem; }}
 details {{ margin-left: 1rem; border-left: 1px solid #8884; padding-left: .6rem; }}
 summary {{ cursor: pointer; }}
 .k {{ color: #0a7; }} .t {{ opacity: .55; font-style: italic; }}
 .v {{ color: #c50; word-break: break-word; }}
</style>
<h1>{title}</h1>
"""


def _render(key: str, value: Any, open_levels: int) -> str:
    key_html = html.escape(str(key))
    if isinstance(value, (dict, list)):
        items = value.items() if isinstance(value, dict) else enumerate(value)
        children = "".join(_render(str(k), v, open_levels - 1) for k, v in items)
        is_open = " open" if open_levels > 0 else ""
        return (f"<details{is_open}><summary><span class='k'>{key_html}</span> "
                f"<span class='t'>{_type_label(value)}</span></summary>{children}</details>")
    return (f"<div><span class='k'>{key_html}</span>: "
            f"<span class='v'>{html.escape(repr(value))}</span> "
            f"<span class='t'>{type(value).__name__}</span></div>")


def inspect(obj: Any, title: str | None = None, open_levels: int = 2,
            path: str | os.PathLike | None = None, show: bool = True) -> Path:
    """Write a collapsible HTML view and open it - drill-down without a notebook."""
    title = title or type(obj).__name__
    plain = to_plain(obj)
    target = Path(path) if path else Path(tempfile.gettempdir()) / f"genaiclass_{id(obj):x}.html"
    body = _render(title, plain, open_levels)
    target.write_text(_HTML_HEAD.format(title=html.escape(title)) + body, encoding="utf-8")
    if show and not os.environ.get("GENAI_NO_BROWSER"):
        webbrowser.open(target.as_uri())
    return target
