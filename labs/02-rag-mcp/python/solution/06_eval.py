"""Lab 2 · stretch — measure before you tune: a tiny golden set checks retrieval (is the right document in the top k?)
and answers (does the answer contain the expected fact?). Re-run it after every change to chunking, model or prompt.
(promptfoo and the Azure AI Evaluation SDK do the same at scale.)"""
import os

from dotenv import find_dotenv, load_dotenv
from pathlib import Path as _Path
from openai import OpenAI

from kestrel_search import Index

_here = _Path(globals().get("__file__", ".")).resolve()   # no __file__ in a notebook: start at the cwd
for _folder in [*_here.parents, _Path.cwd(), *_Path.cwd().parents]:
    if (_folder / ".env").is_file():   # every .env from this file upward: the nearest one wins,
        load_dotenv(_folder / ".env")  # so labs/.env or one .env at the repo root both work
KEY = os.environ["GENAI_API_KEY"]
HEADERS = {"api-key": KEY} if os.getenv("GENAI_KEY_HEADER", "api-key") == "api-key" else None
EXTRA = {"reasoning_effort": os.environ["GENAI_REASONING_EFFORT"]} if os.getenv("GENAI_REASONING_EFFORT") else {}
client = OpenAI(base_url=os.environ["GENAI_BASE_URL"], api_key=KEY, default_headers=HEADERS)
index = Index()

GOLDEN = [  # question, document that must be retrieved, facts the answer must contain
    ("What is the maximum payload of a K-4 Kestrel in rain?", "kestrel_operations_handbook", ["1.8"]),
    ("How long must drones stay grounded after a lightning strike nearby?", "kestrel_operations_handbook", ["30 min"]),
    ("Which form is required before night flights?", "kestrel_operations_handbook", ["NW-17"]),
    ("What does a customer get when the payload is lost?", "kestrel_customer_service_policy", ["full refund", "15"]),
    ("Which latch firmware version fixed the early-release bug?", "kestrel_incident_review_q3_2026", ["3.1.6"]),
    ("How long are proof-of-delivery photos kept?", "kestrel_customer_service_policy", ["30 days"]),
]

retrieval_ok = answer_ok = 0
for question, doc, facts in GOLDEN:
    hits = index.search(question, k=4)
    found = any(h["doc"].startswith(doc) for h in hits)
    sources = "\n\n".join(f"[{n}] {h['text']}" for n, h in enumerate(hits, 1))
    reply = client.chat.completions.create(model=os.environ["GENAI_MODEL"], **EXTRA, messages=[
        {"role": "system", "content": "Answer in one sentence using only these sources:\n" + sources},
        {"role": "user", "content": question}]).choices[0].message.content or ""
    correct = all(f.lower() in reply.lower() for f in facts)
    retrieval_ok += found
    answer_ok += correct
    print(f"{'✓' if found else '✗'} retrieval  {'✓' if correct else '✗'} answer  {question}\n      -> {reply.strip()[:140]}")
print(f"\nretrieval hit@4: {retrieval_ok}/{len(GOLDEN)}   answers correct: {answer_ok}/{len(GOLDEN)}")
