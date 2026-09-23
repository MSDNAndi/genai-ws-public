"""Shared retrieval helper for steps 3-6: load the index from ../../build and search it (cosine top-k)."""
import json
import os
from pathlib import Path

import numpy as np
from dotenv import find_dotenv, load_dotenv
from pathlib import Path as _Path
from openai import OpenAI

_here = _Path(globals().get("__file__", ".")).resolve()   # no __file__ in a notebook: start at the cwd
for _folder in [*_here.parents, _Path.cwd(), *_Path.cwd().parents]:
    if (_folder / ".env").is_file():   # every .env from this file upward: the nearest one wins,
        load_dotenv(_folder / ".env")  # so labs/.env or one .env at the repo root both work
LABS = Path(__file__).resolve().parents[1]   # samples/<segment>/ (was: labs/ root)
LAB2 = LABS
BUILD = LAB2 / "build"


def embed_client() -> OpenAI:
    key = os.getenv("EMBED_API_KEY") or os.environ["GENAI_API_KEY"]
    headers = {"api-key": key} if os.getenv("GENAI_KEY_HEADER", "api-key") == "api-key" else None
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
        self.model = data["embed_model"]
        self.chunks = [{k: v for k, v in item.items() if k != "vector"} for item in data["items"]]
        self.vectors = np.array([item["vector"] for item in data["items"]], dtype=np.float32)
        self.client = embed_client()

    def search(self, query: str, k: int = 4) -> list[dict]:
        q = np.array(self.client.embeddings.create(model=self.model, input=[query], encoding_format="float").data[0].embedding,
                     dtype=np.float32)
        scores = self.vectors @ (q / np.linalg.norm(q))
        best = np.argsort(-scores)[:k]
        return [{**self.chunks[i], "score": round(float(scores[i]), 3)} for i in best]
