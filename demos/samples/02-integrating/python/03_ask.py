# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "genaiclass",
#     "openai==3.18.0",
#     "python-dotenv==1.2.3",
#     "numpy>=1.26",
#     "pydantic>=2.10,<3",
#     "mcp==1.30.0",
#     "markitdown[pdf]==0.1.8",
#     "pillow>=10",
# ]
#
# [tool.uv.sources]
# genaiclass = { path = "../../../shared/python", editable = true }
# ///
# %% [markdown]
# # 03 - Ask with citations (RAG)
#
# retrieve, then answer WITH citations (or admit that the documents don't say).
#
# python 03_ask.py "What is the maximum payload of a K-4 in rain?"
#
# *Ported from the course labs (`labs/02-rag-mcp/python/solution`) on 2026-09-23.*
# %%
import sys
# Windows consoles default to cp1252; one non-ASCII print (a check mark, an arrow)
# kills a demo mid-run. Switch this process's console streams to UTF-8.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, OSError):
        pass
# These samples came from the labs and read GENAI_* variables directly. --profile <name>
# (the runner always passes one) maps a providers.json profile onto those variables, so
# `--profile mock` or `p` in the runner work here exactly like in Segments 1 and 3.
if "--profile" in sys.argv:
    import os
    from genaiclass import get_profile
    _i = sys.argv.index("--profile"); _name = sys.argv[_i + 1]; del sys.argv[_i:_i + 2]
    _p = get_profile(_name)
    os.environ.update(GENAI_BASE_URL=_p.base_url, GENAI_API_KEY=_p.api_key or "none",
                      GENAI_MODEL=_p.model, GENAI_EMBED_MODEL=_p.embed_model,
                      GENAI_KEY_HEADER="api-key" if _p.key_header == "api-key" else "authorization")
    if _name == "mock":                      # the mock has no reasoning knob
        os.environ.pop("GENAI_REASONING_EFFORT", None)
import os
import sys

from dotenv import find_dotenv, load_dotenv
from pathlib import Path as _Path
from openai import OpenAI

from kestrel_search import Index

_here = _Path(globals().get("__file__", ".")).resolve()   # no __file__ in a notebook: start at the cwd
for _folder in [*_here.parents, _Path.cwd(), *_Path.cwd().parents]:
    if (_folder / ".env").is_file():   # every .env from this file upward: the nearest one wins,
        load_dotenv(_folder / ".env")  # so labs/.env or one .env at the repo root both work
BASE, KEY, MODEL = os.environ["GENAI_BASE_URL"], os.environ["GENAI_API_KEY"], os.environ["GENAI_MODEL"]
HEADERS = {"api-key": KEY} if os.getenv("GENAI_KEY_HEADER", "api-key") == "api-key" else None
client = OpenAI(base_url=BASE, api_key=KEY, default_headers=HEADERS)
# Optional: GENAI_REASONING_EFFORT=low (gpt-5 family) or none (local "thinking" models) keeps answers fast and cheap
EXTRA = {"reasoning_effort": os.environ["GENAI_REASONING_EFFORT"]} if os.getenv("GENAI_REASONING_EFFORT") else {}
index = Index()

QUESTIONS = sys.argv[1:] or [
    "What is the maximum payload of a K-4 Kestrel in rain?",
    "A Standard delivery arrived 41 minutes late. What does the customer get?",
    "Which latch firmware version fixed the early-release bug?",
    "Who is the CEO of Kestrel?",                         # not in the documents -> must say so
]

for question in QUESTIONS:
    hits = index.search(question, k=4)
    sources = "\n\n".join(f"[{n}] ({h['doc']})\n{h['text']}" for n, h in enumerate(hits, 1))
    # >>> TODO 2: write the grounding instructions: answer only from the numbered sources, cite them like [2], say "not in the documents" otherwise
    system = ("You answer questions about Kestrel Drone Logistics using ONLY the numbered sources below. "
              "Cite every fact with its source number in square brackets, e.g. [2]. If the sources do not contain "
              "the answer, reply exactly: Not in the documents.\n\nSOURCES:\n" + sources)
    # <<< TODO
    r = client.chat.completions.create(model=MODEL, **EXTRA, messages=[{"role": "system", "content": system},
                                                              {"role": "user", "content": question}])
    print(f"\nQ: {question}\nA: {r.choices[0].message.content.strip()}")
    print("   sources: " + "; ".join(f"[{n}] {h['id']} ({h['score']})" for n, h in enumerate(hits, 1)))
