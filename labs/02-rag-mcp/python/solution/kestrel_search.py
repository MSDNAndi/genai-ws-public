"""Shared retrieval helper for steps 3-6: load build/index.json and search it.

search = embed the question with the SAME model as the chunks, score every chunk by cosine similarity (how close two
vectors point; 1 = same meaning), return the top k (the k best chunks). No database: a few hundred vectors fit in memory.
"""
import json
import os
from pathlib import Path

import numpy as np
from dotenv import find_dotenv, load_dotenv
from pathlib import Path as _Path
from openai import OpenAI

# --- settings: load labs/.env ----------------------------------------------------------------------------------------
_here = _Path(globals().get("__file__", ".")).resolve()   # no __file__ in a notebook: start at the cwd
for _folder in [*_here.parents, _Path.cwd(), *_Path.cwd().parents]:
    if (_folder / ".env").is_file():   # every .env from this file upward: the nearest one wins,
        load_dotenv(_folder / ".env")  # so labs/.env or one .env at the repo root both work
LABS = next(p for p in Path(__file__).resolve().parents if (p / "_tools" / "make_starters.py").exists())  # labs/ root
LAB2 = LABS / "02-rag-mcp"
BUILD = LAB2 / "build"


def embed_client() -> OpenAI:
    """Client for the embeddings endpoint (EMBED_* if you embed somewhere else, otherwise the normal GENAI_*)."""
    key = os.getenv("EMBED_API_KEY") or os.environ["GENAI_API_KEY"]
    headers = {"api-key": key} if os.getenv("GENAI_KEY_HEADER", "api-key") == "api-key" else None   # Azure-style "api-key" header
    return OpenAI(base_url=os.getenv("EMBED_BASE_URL") or os.environ["GENAI_BASE_URL"], api_key=key, default_headers=headers)


class Index:
    """build/index.json = {"embed_model", "dims", "items": [{id, doc, chunk, text, vector}]} (written by 02_embed.py)."""

    def __init__(self):
        path = BUILD / "index.json"
        if not path.exists():
            # Fresh clone, step 2 never ran: build the index now (02_embed falls back to the prebuilt
            # chunks), so steps 3-6 also work on their own, e.g. straight from the demo menu.
            import subprocess, sys
            print(f"{path.name} missing - building it first (02_embed.py) ...", flush=True)
            subprocess.run([sys.executable, str(Path(__file__).with_name("02_embed.py"))], check=True)
        if not path.exists():
            raise SystemExit(f"{path} not found - run 01_ingest.py and 02_embed.py first")
        data = json.loads(path.read_text(encoding="utf-8"))
        self.model = data["embed_model"]             # queries must be embedded with the model the index was built with
        self.chunks = [{k: v for k, v in item.items() if k != "vector"} for item in data["items"]]
        self.vectors = np.array([item["vector"] for item in data["items"]], dtype=np.float32)   # one row per chunk
        self.client = embed_client()

    def search(self, query: str, k: int = 4) -> list[dict]:
        """The k chunks closest in meaning to the query, best first, each with a similarity score."""
        q = np.array(self.client.embeddings.create(model=self.model, input=[query], encoding_format="float").data[0].embedding,
                     dtype=np.float32)
        scores = self.vectors @ (q / np.linalg.norm(q))   # rows are unit vectors, so dot product = cosine similarity
        best = np.argsort(-scores)[:k]                     # indices of the k highest scores
        return [{**self.chunks[i], "score": round(float(scores[i]), 3)} for i in best]
