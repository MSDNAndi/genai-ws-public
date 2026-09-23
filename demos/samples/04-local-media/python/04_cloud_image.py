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
# # 04 - Cloud image generation
#
# no GPU? The same idea in the cloud: an image model behind the SAME OpenAI-compatible endpoint.
#
# Uses GENAI_IMAGE_MODEL (e.g. gpt-image-1-mini on Foundry). Log the prompt and settings next to the image as well.
#
# *Ported from the course labs (`labs/04-local-media/python/solution`) on 2026-09-23.*
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
