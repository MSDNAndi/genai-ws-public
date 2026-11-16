"""Minimal ComfyUI client for Lab 4 (stdlib + httpx) - the helper that steps 2, 3 and 6 import.

A ComfyUI workflow is a graph of nodes saved as JSON. In *API format* (Workflow -> Export (API)) it is simply
{"node id": {"class_type": "KSampler", "inputs": {"seed": 42, "cfg": 5, ...}}, ...}. Three functions:
  load(path)        read the file
  patch(wf, ...)    change a few inputs (prompt, seed, cfg ...) in a copy of the graph
  run(wf, out_dir)  send it to ComfyUI, wait until it is done, download the images
ComfyUI's HTTP API used by run(): POST /prompt (queue the job) · GET /history/<id> (done yet?) · GET /view (the image).

Knobs are matched by input name on ANY node, so the same code drives SD/SDXL/Flux/Z-Image style graphs:
  seed -> seed | noise_seed · steps -> steps · cfg -> cfg | guidance · denoise -> denoise · width/height -> width/height
The positive/negative prompt is found by following the sampler's (or guider's) "positive"/"negative" links.
"""
import copy
import json
import os
import time
import uuid
from pathlib import Path

import httpx

# knob name -> input names it may have on a node (Flux calls cfg "guidance", some samplers call seed "noise_seed")
KNOB_INPUTS = {"seed": ("seed", "noise_seed"), "steps": ("steps",), "cfg": ("cfg", "guidance"),
               "denoise": ("denoise",), "width": ("width",), "height": ("height",)}


def load(path: str | Path) -> dict:
    """Read an API-format workflow file and return it as a dict."""
    wf = json.loads(Path(path).read_text(encoding="utf-8"))
    if "nodes" in wf and "links" in wf:
        raise SystemExit(f"{path} is a UI-format workflow - in ComfyUI use Workflow > Export (API) and save that file.")
    for key in [k for k, v in wf.items() if not isinstance(v, dict)]:   # e.g. a "_note" the author left in the file
        print(f"   note in {Path(path).name}: {wf.pop(key)}")
    return wf


def _prompt_node(wf: dict, which: str) -> str | None:
    """Find the text node wired into a sampler's "positive" or "negative" input; returns its node id."""
    for node in wf.values():
        link = node.get("inputs", {}).get(which)
        # in API format a wire is a list [source node id, output index]; a plain value is a number or string
        if isinstance(link, list) and wf.get(str(link[0]), {}).get("class_type", "").startswith("CLIPTextEncode"):
            return str(link[0])
    return None


def patch(wf: dict, prompt: str | None = None, negative: str | None = None, **knobs) -> dict:
    """Return a COPY of the workflow with new prompt/negative text and knob values (None = keep the file's value)."""
    wf = copy.deepcopy(wf)   # a copy, so the same base workflow can be patched again and again (step 3)
    for knob, value in knobs.items():
        if value is None:
            continue
        hit = False
        for node in wf.values():
            for name in KNOB_INPUTS[knob]:
                # only overwrite plain values - a list here is a wire from another node, leave it alone
                if name in node.get("inputs", {}) and not isinstance(node["inputs"][name], list):
                    node["inputs"][name] = value
                    hit = True
        if not hit:
            print(f"   (no '{knob}' input in this workflow - ignored)")
    for text, which in ((prompt, "positive"), (negative, "negative")):
        node_id = _prompt_node(wf, which) if text else None
        if node_id:
            wf[node_id]["inputs"]["text"] = text
    return wf


def run(wf: dict, out_dir: str | Path, base: str | None = None, timeout: float = 900) -> list[Path]:
    """Queue the workflow on ComfyUI (COMFYUI_URL), wait for it, save every output image; returns the file paths."""
    base = (base or os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")).rstrip("/")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    try:   # quick "is ComfyUI running?" check, so you get a clear message instead of a stack trace
        httpx.get(base + "/system_stats", timeout=5).raise_for_status()
    except httpx.HTTPError:
        raise SystemExit(f"ComfyUI is not reachable at {base}. No GPU / in a codespace? Start the stand-in in a second "
                         f"terminal:  python _tools/comfy_mock.py 8188  from labs/  (or skip to step 4, the cloud path).")
    with httpx.Client(base_url=base, timeout=60) as http:
        # 1. queue the job - ComfyUI calls a queued workflow a "prompt" and answers with its id
        prompt_id = http.post("/prompt", json={"prompt": wf, "client_id": uuid.uuid4().hex}).raise_for_status().json()["prompt_id"]
        # 2. ask once a second whether the job is finished (it appears in /history when done)
        deadline = time.time() + timeout
        while time.time() < deadline:
            history = http.get(f"/history/{prompt_id}").raise_for_status().json()
            if prompt_id in history:
                break
            time.sleep(1)
        else:
            raise TimeoutError(f"ComfyUI did not finish {prompt_id} in {timeout}s")
        # 3. download every image the workflow produced into out_dir
        saved = []
        for node_output in history[prompt_id].get("outputs", {}).values():
            for img in node_output.get("images", []):
                data = http.get("/view", params={"filename": img["filename"], "subfolder": img.get("subfolder", ""),
                                                 "type": img.get("type", "output")}).raise_for_status().content
                target = out_dir / img["filename"]
                target.write_bytes(data)
                saved.append(target)
        return saved
