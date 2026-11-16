"""Lab 2 · step 2 — embed: chunk -> vector -> store.

An embedding (text as a list of numbers) puts similar meanings close together, so "search" becomes "find the
nearest vectors". We embed every chunk with the /embeddings endpoint (same OpenAI client as Lab 1) and save chunks +
vectors in build/index.json — the simplest possible vector store (a searchable file of vectors).
Notice: we batch 32 chunks per request, and normalise each vector once so search is a plain dot product.
Optional: EMBED_BASE_URL / EMBED_API_KEY / GENAI_EMBED_MODEL embed locally (e.g. Ollama bge-m3) while chatting in the cloud.
"""
import json
import os
import time
from pathlib import Path

import numpy as np
from dotenv import find_dotenv, load_dotenv
from pathlib import Path as _Path
from openai import OpenAI

# --- settings: load labs/.env (your key, endpoint and model names) -----------------------------------------------------
_here = _Path(globals().get("__file__", ".")).resolve()   # no __file__ in a notebook: start at the cwd
for _folder in [*_here.parents, _Path.cwd(), *_Path.cwd().parents]:
    if (_folder / ".env").is_file():   # every .env from this file upward: the nearest one wins,
        load_dotenv(_folder / ".env")  # so labs/.env or one .env at the repo root both work
KEY = os.getenv("EMBED_API_KEY") or os.environ["GENAI_API_KEY"]        # EMBED_* only if you embed somewhere else
BASE = os.getenv("EMBED_BASE_URL") or os.environ["GENAI_BASE_URL"]
EMBED_MODEL = os.environ["GENAI_EMBED_MODEL"]
HEADERS = {"api-key": KEY} if os.getenv("GENAI_KEY_HEADER", "api-key") == "api-key" else None   # Azure-style "api-key" header
client = OpenAI(base_url=BASE, api_key=KEY, default_headers=HEADERS)

# --- input: your chunks from step 1, or the prebuilt copy (C#/TypeScript, or if step 1 was skipped) -------------------
LABS = next(p for p in Path(__file__).resolve().parents if (p / "_tools" / "make_starters.py").exists())  # labs/ root
BUILD = LABS / "02-rag-mcp" / "build"
source = BUILD / "chunks.jsonl" if (BUILD / "chunks.jsonl").exists() else LABS / "02-rag-mcp" / "data" / "prebuilt" / "chunks.jsonl"
chunks = [json.loads(line) for line in open(source, encoding="utf-8")]

# --- embed: text in, one vector per text out ------------------------------------------------------------------------
t0, vectors = time.perf_counter(), []
for i in range(0, len(chunks), 32):                  # batch: one request per 32 chunks
    batch = chunks[i:i + 32]
    r = client.embeddings.create(model=EMBED_MODEL, input=[c["text"] for c in batch], encoding_format="float")
    vectors += [d.embedding for d in r.data]         # same order as the input
matrix = np.array(vectors, dtype=np.float32)
matrix /= np.linalg.norm(matrix, axis=1, keepdims=True)   # normalise once -> cosine similarity = dot product

# --- store: chunks + vectors + the model name (queries must use the SAME model) --------------------------------------
BUILD.mkdir(exist_ok=True)
index = {"embed_model": EMBED_MODEL, "dims": int(matrix.shape[1]),
         "items": [{**c, "vector": [round(float(x), 6) for x in row]} for c, row in zip(chunks, matrix)]}
(BUILD / "index.json").write_text(json.dumps(index), encoding="utf-8")   # one plain file = our "vector store"
print(f"{len(chunks)} chunks x {matrix.shape[1]} dims with '{EMBED_MODEL}' in {time.perf_counter() - t0:.1f}s "
      f"-> build/index.json")
