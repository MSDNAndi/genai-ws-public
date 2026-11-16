# STARTER - complete the TODO block(s). The finished version is in solution/03_one_knob.py
"""Lab 4 · step 3 — change ONE knob at a time and put the results side by side.

What this shows: we render the same workflow several times, changing only one setting (the "knob") and keeping the
seed fixed. Then we paste all images into one "contact sheet" (a row of labelled thumbnails).
What to notice: because everything else stays the same, any difference you see comes from that one knob.
Craft principle #2: change one thing at a time.

    python 03_one_knob.py ../comfyui_workflows/01_txt2img_sdxl.json --knob cfg --values 1.5 3 5 8 --seed 42 --prompt "..."

Knobs: seed (random starting noise) · steps (denoising passes) · cfg (how strictly to follow the prompt) ·
denoise (how much of the start image to repaint). In a codespace start  python _tools/comfy_mock.py 8188  first.
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw   # Pillow: open, paste and label images

import comfy   # our small ComfyUI helper in this folder: load(), patch(), run()

ap = argparse.ArgumentParser()
ap.add_argument("workflow")
ap.add_argument("--knob", choices=["seed", "steps", "cfg", "denoise"], default="cfg")
ap.add_argument("--values", nargs="+", required=True, help="one render per value, e.g. 1.5 3 5 8")
ap.add_argument("--seed", type=int, default=42, help="fixed, so only the knob changes")
ap.add_argument("--prompt")
ap.add_argument("--out", default="out/one_knob")
a = ap.parse_args()

# One render per value. Everything else (prompt, seed, model) stays the same.
base = comfy.load(a.workflow)
tiles = []   # (label, image) pairs for the contact sheet
for raw in a.values:
    value = int(raw) if a.knob in ("seed", "steps") else float(raw)   # seed/steps are whole numbers
    knobs = {"seed": a.seed, a.knob: value}   # if the knob IS seed, this value replaces the fixed seed
    images = comfy.run(comfy.patch(base, prompt=a.prompt, **knobs), Path(a.out) / f"{a.knob}_{raw}")
    if images:
        tiles.append((f"{a.knob}={raw}", Image.open(images[0]).convert("RGB")))
        print(f"{a.knob}={raw}: {images[0]}")

# The contact sheet: one row of tiles, a 30-pixel white strip on top for the labels.
# TODO 1: paste the tiles into one contact sheet, label each tile, save it as <out>/contact_<knob>.png
raise NotImplementedError("TODO 1: paste the tiles into one contact sheet, label each tile, save it as <out>/contact_<knob>.png")
print(f"contact sheet: {sheet_path}  - what changed, and what stayed the same?")
