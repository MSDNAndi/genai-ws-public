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
# # 03 - One knob at a time
#
# change ONE knob at a time and put the results side by side (craft principle #2).
#
# python 03_one_knob.py ../comfyui_workflows/01_txt2img_sdxl.json --knob cfg --values 1.5 3 5 8 --seed 42 --prompt "..."
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
if len(sys.argv) == 1:   # started from the menu without a workflow: explain instead of an argparse error
    print("This demo drives a local ComfyUI (default http://127.0.0.1:8188, set COMFYUI_URL) with a workflow file.")
    print("Run it like this:  uv run 03_one_knob.py ../comfyui_workflows/01_txt2img_sdxl.json --values 20,30,40")
    print("No ComfyUI on this machine? Demo 4.04 generates an image in the cloud instead.")
    sys.exit(0)
import argparse
from pathlib import Path

from PIL import Image, ImageDraw

import comfy

ap = argparse.ArgumentParser()
ap.add_argument("workflow")
ap.add_argument("--knob", choices=["seed", "steps", "cfg", "denoise"], default="cfg")
ap.add_argument("--values", nargs="+", required=True)
ap.add_argument("--seed", type=int, default=42)
ap.add_argument("--prompt")
ap.add_argument("--out", default="out/one_knob")
a = ap.parse_args()

base = comfy.load(a.workflow)
tiles = []
for raw in a.values:
    value = int(raw) if a.knob in ("seed", "steps") else float(raw)
    knobs = {"seed": a.seed, a.knob: value}
    images = comfy.run(comfy.patch(base, prompt=a.prompt, **knobs), Path(a.out) / f"{a.knob}_{raw}")
    if images:
        tiles.append((f"{a.knob}={raw}", Image.open(images[0]).convert("RGB")))
        print(f"{a.knob}={raw}: {images[0]}")

# >>> TODO 1: paste the tiles into one contact sheet, label each tile, save it as <out>/contact_<knob>.png
w, h = tiles[0][1].size
sheet = Image.new("RGB", (w * len(tiles), h + 30), "white")
draw = ImageDraw.Draw(sheet)
for i, (label, img) in enumerate(tiles):
    sheet.paste(img.resize((w, h)), (i * w, 30))
    draw.text((i * w + 8, 8), label, fill="black")
sheet_path = Path(a.out) / f"contact_{a.knob}.png"
sheet.save(sheet_path)
# <<< TODO
print(f"contact sheet: {sheet_path}  - what changed, and what stayed the same?")
