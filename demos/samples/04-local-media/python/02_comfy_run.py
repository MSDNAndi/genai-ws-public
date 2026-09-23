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
# # 02 - ComfyUI from code - log the seed
#
# run a ComfyUI workflow from code and LOG THE SEED (craft principle #1: you can only improve what you
#
# can reproduce). Every image gets a sidecar .json with the exact settings.
#
# python 02_comfy_run.py ../comfyui_workflows/01_txt2img_sdxl.json --prompt "a lighthouse in fog, 35mm photo" --seed 42
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
    print("Run it like this:  uv run 02_comfy_run.py ../comfyui_workflows/01_txt2img_sdxl.json")
    print("No ComfyUI on this machine? Demo 4.04 generates an image in the cloud instead.")
    sys.exit(0)
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
