"""Lab 2 · step 2 — embed every chunk and keep the vectors in a plain numpy file (the simplest "vector store").

Same OpenAI-compatible client as Lab 1, different endpoint: /embeddings. Works with Foundry (text-embedding-3-*)
and with Ollama (bge-m3, nomic-embed-text ...) — just change GENAI_EMBED_MODEL, or set EMBED_BASE_URL/EMBED_API_KEY
to embed locally while chatting in the cloud.
"""
import json
import os
import time
from pathlib import Path

import numpy as np
from dotenv import find_dotenv, load_dotenv
from pathlib import Path as _Path
from openai import OpenAI

_here = _Path(globals().get("__file__", ".")).resolve()   # no __file__ in a notebook: start at the cwd
for _folder in [*_here.parents, _Path.cwd(), *_Path.cwd().parents]:
    if (_folder / ".env").is_file():   # every .env from this file upward: the nearest one wins,
        load_dotenv(_folder / ".env")  # so labs/.env or one .env at the repo root both work
KEY = os.getenv("EMBED_API_KEY") or os.environ["GENAI_API_KEY"]
BASE = os.getenv("EMBED_BASE_URL") or os.environ["GENAI_BASE_URL"]
EMBED_MODEL = os.environ["GENAI_EMBED_MODEL"]
HEADERS = {"api-key": KEY} if os.getenv("GENAI_KEY_HEADER", "api-key") == "api-key" else None
client = OpenAI(base_url=BASE, api_key=KEY, default_headers=HEADERS)

LABS = next(p for p in Path(__file__).resolve().parents if (p / "_tools" / "make_starters.py").exists())  # labs/ root
BUILD = LABS / "02-rag-mcp" / "build"
source = BUILD / "chunks.jsonl" if (BUILD / "chunks.jsonl").exists() else LABS / "02-rag-mcp" / "data" / "prebuilt" / "chunks.jsonl"
chunks = [json.loads(line) for line in open(source, encoding="utf-8")]

t0, vectors = time.perf_counter(), []
for i in range(0, len(chunks), 32):                  # batch: one request per 32 chunks
    batch = chunks[i:i + 32]
    r = client.embeddings.create(model=EMBED_MODEL, input=[c["text"] for c in batch], encoding_format="float")
    vectors += [d.embedding for d in r.data]
matrix = np.array(vectors, dtype=np.float32)
matrix /= np.linalg.norm(matrix, axis=1, keepdims=True)   # normalise once -> cosine similarity = dot product

BUILD.mkdir(exist_ok=True)
index = {"embed_model": EMBED_MODEL, "dims": int(matrix.shape[1]),
         "items": [{**c, "vector": [round(float(x), 6) for x in row]} for c, row in zip(chunks, matrix)]}
(BUILD / "index.json").write_text(json.dumps(index), encoding="utf-8")   # one plain file = our "vector store"
print(f"{len(chunks)} chunks x {matrix.shape[1]} dims with '{EMBED_MODEL}' in {time.perf_counter() - t0:.1f}s "
      f"-> build/index.json")
