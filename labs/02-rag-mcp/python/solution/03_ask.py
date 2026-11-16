"""Lab 2 · step 3 — ask: retrieve top-k -> put them into the prompt -> answer WITH citations.

For each question we fetch the 4 most similar chunks, number them [1]..[4] and paste them into the system prompt.
Grounding (answer only from given sources) is just instructions: use only the sources, cite them, or say
"Not in the documents". Notice the CEO question: no retrieved chunk holds the answer, so the model must refuse.

    python 03_ask.py "What is the maximum payload of a K-4 in rain?"
"""
import os
import sys

from dotenv import find_dotenv, load_dotenv
from pathlib import Path as _Path
from openai import OpenAI

from kestrel_search import Index                      # step 2's index + search(), shared by steps 3-6

# --- settings: load labs/.env and connect (same as Lab 1) -------------------------------------------------------------
_here = _Path(globals().get("__file__", ".")).resolve()   # no __file__ in a notebook: start at the cwd
for _folder in [*_here.parents, _Path.cwd(), *_Path.cwd().parents]:
    if (_folder / ".env").is_file():   # every .env from this file upward: the nearest one wins,
        load_dotenv(_folder / ".env")  # so labs/.env or one .env at the repo root both work
BASE, KEY, MODEL = os.environ["GENAI_BASE_URL"], os.environ["GENAI_API_KEY"], os.environ["GENAI_MODEL"]
HEADERS = {"api-key": KEY} if os.getenv("GENAI_KEY_HEADER", "api-key") == "api-key" else None   # Azure-style "api-key" header
client = OpenAI(base_url=BASE, api_key=KEY, default_headers=HEADERS)
# GENAI_REASONING_EFFORT (optional, from labs/.env) keeps thinking models fast; the gateway drops it for models that
# don't support it. Local "thinking" models: use none.
EXTRA = {"reasoning_effort": os.environ["GENAI_REASONING_EFFORT"]} if os.getenv("GENAI_REASONING_EFFORT") else {}
index = Index()

QUESTIONS = sys.argv[1:] or [
    "What is the maximum payload of a K-4 Kestrel in rain?",
    "A Standard delivery arrived 41 minutes late. What does the customer get?",
    "Which latch firmware version fixed the early-release bug?",
    "Who is the CEO of Kestrel?",                         # not in the documents -> must say so
]

for question in QUESTIONS:
    # 1. retrieve: the 4 chunks closest in meaning to the question
    hits = index.search(question, k=4)
    # 2. number them, so the model can cite [1], [2] ... and we can map citations back to chunk ids
    sources = "\n\n".join(f"[{n}] ({h['doc']})\n{h['text']}" for n, h in enumerate(hits, 1))
    # 3. ground: the rules + the sources go into the system prompt; the user message stays just the question
    # >>> TODO 2: write the grounding instructions: answer only from the numbered sources, cite them like [2], say "not in the documents" otherwise
    system = ("You answer questions about Kestrel Drone Logistics using ONLY the numbered sources below. "
              "Cite every fact with its source number in square brackets, e.g. [2]. If the sources do not contain "
              "the answer, reply exactly: Not in the documents.\n\nSOURCES:\n" + sources)
    # <<< TODO
    # 4. generate: a normal chat call, as in Lab 1
    r = client.chat.completions.create(model=MODEL, **EXTRA, messages=[{"role": "system", "content": system},
                                                              {"role": "user", "content": question}])
    print(f"\nQ: {question}\nA: {r.choices[0].message.content.strip()}")
    # show what [1]..[4] were, so you can check every citation yourself
    print("   sources: " + "; ".join(f"[{n}] {h['id']} ({h['score']})" for n, h in enumerate(hits, 1)))
