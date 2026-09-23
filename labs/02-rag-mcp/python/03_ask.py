# STARTER - complete the TODO block(s). The finished version is in solution/03_ask.py
"""Lab 2 · step 3 — retrieve, then answer WITH citations (or admit that the documents don't say).

python 03_ask.py "What is the maximum payload of a K-4 in rain?"
"""
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
    # TODO 2: write the grounding instructions: answer only from the numbered sources, cite them like [2], say 'not in the documents' otherwise
    raise NotImplementedError("TODO 2: write the grounding instructions: answer only from the numbered sources, cite them like [2], say 'not in the documents' otherwise")
    r = client.chat.completions.create(model=MODEL, **EXTRA, messages=[{"role": "system", "content": system},
                                                              {"role": "user", "content": question}])
    print(f"\nQ: {question}\nA: {r.choices[0].message.content.strip()}")
    print("   sources: " + "; ".join(f"[{n}] {h['id']} ({h['score']})" for n, h in enumerate(hits, 1)))
