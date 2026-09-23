"""Lab 4 · step 2 — run a ComfyUI workflow from code and LOG THE SEED (craft principle #1: you can only improve what you
can reproduce). Every image gets a sidecar .json with the exact settings.

python 02_comfy_run.py ../comfyui_workflows/01_txt2img_sdxl.json --prompt "a lighthouse in fog, 35mm photo" --seed 42
"""
import argparse
import json
import random
from pathlib import Path

import comfy

ap = argparse.ArgumentParser()
ap.add_argument("workflow", help="ComfyUI workflow in API format (.json)")
ap.add_argument("--prompt")
ap.add_argument("--negative")
ap.add_argument("--seed", type=int, help="omit for a random seed (it is still logged)")
ap.add_argument("--steps", type=int)
ap.add_argument("--cfg", type=float)
ap.add_argument("--denoise", type=float)
ap.add_argument("--out", default="out")
a = ap.parse_args()

seed = a.seed if a.seed is not None else random.randint(0, 2**31 - 1)
settings = {"workflow": Path(a.workflow).name, "prompt": a.prompt, "negative": a.negative, "seed": seed,
            "steps": a.steps, "cfg": a.cfg, "denoise": a.denoise}
wf = comfy.patch(comfy.load(a.workflow), prompt=a.prompt, negative=a.negative, seed=seed, steps=a.steps, cfg=a.cfg,
                 denoise=a.denoise)
for image in comfy.run(wf, a.out):
    image.with_suffix(".json").write_text(json.dumps(settings, indent=2), encoding="utf-8")
    print(f"saved {image}  (seed {seed})")
