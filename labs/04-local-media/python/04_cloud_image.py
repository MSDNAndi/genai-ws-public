"""Lab 4 · step 4 — no GPU? The same idea in the cloud: an image model behind the SAME OpenAI-compatible endpoint.

Uses GENAI_IMAGE_MODEL (e.g. gpt-image-1-mini on Foundry). Log the prompt and settings next to the image as well.
"""
import base64
import json
import os
import time
from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from pathlib import Path as _Path
from openai import OpenAI

_here = _Path(globals().get("__file__", ".")).resolve()   # no __file__ in a notebook: start at the cwd
for _folder in [*_here.parents, _Path.cwd(), *_Path.cwd().parents]:
    if (_folder / ".env").is_file():   # every .env from this file upward: the nearest one wins,
        load_dotenv(_folder / ".env")  # so labs/.env or one .env at the repo root both work
KEY = os.environ["GENAI_API_KEY"]
HEADERS = {"api-key": KEY} if os.getenv("GENAI_KEY_HEADER", "api-key") == "api-key" else None
client = OpenAI(base_url=os.environ["GENAI_BASE_URL"], api_key=KEY, default_headers=HEADERS, timeout=300)
MODEL = os.getenv("GENAI_IMAGE_MODEL", "gpt-image-1-mini")

prompt = "A small delivery drone carrying a parcel over a river at dawn, watercolor, soft light"
settings = {"model": MODEL, "prompt": prompt, "size": "1024x1024", "quality": "low", "n": 1}
t0 = time.perf_counter()
result = client.images.generate(**settings)
out = Path("out")
out.mkdir(exist_ok=True)
stamp = time.strftime("%Y%m%d-%H%M%S")
for i, image in enumerate(result.data):
    target = out / f"cloud_{stamp}_{i}.png"
    target.write_bytes(base64.b64decode(image.b64_json))
    target.with_suffix(".json").write_text(json.dumps(settings, indent=2), encoding="utf-8")
    print(f"saved {target} in {time.perf_counter() - t0:.1f}s")
# Note: cloud image APIs have no seed you can pin — compare that with step 2. Quality low/medium/high changes cost.
