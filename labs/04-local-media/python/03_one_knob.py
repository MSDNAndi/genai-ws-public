# STARTER - complete the TODO block(s). The finished version is in solution/03_one_knob.py
"""Lab 4 · step 3 — change ONE knob at a time and put the results side by side (craft principle #2).

python 03_one_knob.py ../comfyui_workflows/01_txt2img_sdxl.json --knob cfg --values 1.5 3 5 8 --seed 42 --prompt "..."
"""
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

# TODO 1: paste the tiles into one contact sheet, label each tile, save it as <out>/contact_<knob>.png
raise NotImplementedError("TODO 1: paste the tiles into one contact sheet, label each tile, save it as <out>/contact_<knob>.png")
print(f"contact sheet: {sheet_path}  - what changed, and what stayed the same?")
