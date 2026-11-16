"""Lab 4 · step 4 — no GPU? Generate the image in the cloud instead.

What this shows: an image model sits behind the SAME OpenAI-compatible endpoint and key as the chat models from Lab 1.
One call (`client.images.generate`) returns the picture as base64 text; we decode it and save a .png, plus a .json
with the settings - the same logging habit as step 2.
What to notice: there is no seed to pin here, so the same prompt gives a different picture every time.

Uses GENAI_IMAGE_MODEL (gpt-image-1-mini on the workshop endpoint). Limit: 3 images per minute per key.
"""
import base64
import json
import os
import time
from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from pathlib import Path as _Path
from openai import OpenAI

# Load the settings file (labs/.env). Real environment variables win over the file.
_here = _Path(globals().get("__file__", ".")).resolve()   # no __file__ in a notebook: start at the cwd
for _folder in [*_here.parents, _Path.cwd(), *_Path.cwd().parents]:
    if (_folder / ".env").is_file():   # every .env from this file upward: the nearest one wins,
        load_dotenv(_folder / ".env")  # so labs/.env or one .env at the repo root both work

# The same client as in Lab 1. The workshop gateway wants the key in an "api-key" header.
KEY = os.environ["GENAI_API_KEY"]
HEADERS = {"api-key": KEY} if os.getenv("GENAI_KEY_HEADER", "api-key") == "api-key" else None
client = OpenAI(base_url=os.environ["GENAI_BASE_URL"], api_key=KEY, default_headers=HEADERS, timeout=300)
MODEL = os.getenv("GENAI_IMAGE_MODEL", "gpt-image-1-mini")

# Everything we send is kept in one dict, so we can save exactly that next to the image.
prompt = "A small delivery drone carrying a parcel over a river at dawn, watercolor, soft light"
settings = {"model": MODEL, "prompt": prompt, "size": "1024x1024", "quality": "low", "n": 1}   # low = cheapest, fastest
t0 = time.perf_counter()
result = client.images.generate(**settings)

out = Path("out")
out.mkdir(exist_ok=True)
stamp = time.strftime("%Y%m%d-%H%M%S")   # a timestamp in the name, so runs never overwrite each other
for i, image in enumerate(result.data):
    target = out / f"cloud_{stamp}_{i}.png"
    target.write_bytes(base64.b64decode(image.b64_json))   # the picture arrives as base64 text -> bytes -> .png
    target.with_suffix(".json").write_text(json.dumps(settings, indent=2), encoding="utf-8")   # the recipe
    print(f"saved {target} in {time.perf_counter() - t0:.1f}s")
# Note: cloud image APIs have no seed you can pin — compare that with step 2. Quality low/medium/high changes cost.
