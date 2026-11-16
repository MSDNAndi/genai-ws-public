"""Lab 4 · step 2 — run a ComfyUI workflow from code and LOG THE SEED.

What this shows: ComfyUI (a local image generator) runs a "workflow JSON" (the node graph saved as a file). We load
that file, change a few inputs, run it and save the image - plus a .json "sidecar" file with the exact settings.
What to notice: the seed (the random starting noise) decides the picture. Same seed + same settings = same image.
Craft principle #1: you can only improve what you can reproduce.

    python 02_comfy_run.py ../comfyui_workflows/01_txt2img_sdxl.json --prompt "a lighthouse in fog, 35mm photo" --seed 42

In a codespace (no GPU): first start the stand-in in a second terminal, from labs/:  python _tools/comfy_mock.py 8188
"""
import argparse
import json
import random
from pathlib import Path

import comfy   # our small ComfyUI helper in this folder: load(), patch(), run()

# Command-line options. Anything you leave out keeps the value saved in the workflow file.
ap = argparse.ArgumentParser()
ap.add_argument("workflow", help="ComfyUI workflow in API format (.json)")
ap.add_argument("--prompt", help="what you want to see")
ap.add_argument("--negative", help="what you do NOT want to see")
ap.add_argument("--seed", type=int, help="omit for a random seed (it is still logged)")
ap.add_argument("--steps", type=int, help="denoising steps: more = slower, usually finer")
ap.add_argument("--cfg", type=float, help="how strictly to follow the prompt")
ap.add_argument("--denoise", type=float, help="1.0 = start from pure noise")
ap.add_argument("--out", default="out")
a = ap.parse_args()

# No seed given? Pick one ourselves - so we still know it and can log it.
seed = a.seed if a.seed is not None else random.randint(0, 2**31 - 1)
settings = {"workflow": Path(a.workflow).name, "prompt": a.prompt, "negative": a.negative, "seed": seed,
            "steps": a.steps, "cfg": a.cfg, "denoise": a.denoise}

# load the workflow file -> change the inputs we were given -> run it on ComfyUI
wf = comfy.patch(comfy.load(a.workflow), prompt=a.prompt, negative=a.negative, seed=seed, steps=a.steps, cfg=a.cfg,
                 denoise=a.denoise)
for image in comfy.run(wf, a.out):
    # the sidecar: out/xyz.png gets out/xyz.json with the exact recipe
    image.with_suffix(".json").write_text(json.dumps(settings, indent=2), encoding="utf-8")
    print(f"saved {image}  (seed {seed})")
