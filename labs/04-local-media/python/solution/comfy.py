"""Minimal ComfyUI API client for Lab 4 (stdlib + httpx). ComfyUI runs workflows saved in *API format*
(Workflow -> Export (API)); we patch a few inputs, queue the prompt, poll the history, download the images.

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

KNOB_INPUTS = {"seed": ("seed", "noise_seed"), "steps": ("steps",), "cfg": ("cfg", "guidance"),
               "denoise": ("denoise",), "width": ("width",), "height": ("height",)}


def load(path: str | Path) -> dict:
    wf = json.loads(Path(path).read_text(encoding="utf-8"))
    if "nodes" in wf and "links" in wf:
        raise SystemExit(f"{path} is a UI-format workflow - in ComfyUI use Workflow > Export (API) and save that file.")
    for key in [k for k, v in wf.items() if not isinstance(v, dict)]:   # e.g. a "_note" the author left in the file
        print(f"   note in {Path(path).name}: {wf.pop(key)}")
    return wf


def _prompt_node(wf: dict, which: str) -> str | None:
    for node in wf.values():
        link = node.get("inputs", {}).get(which)
        if isinstance(link, list) and wf.get(str(link[0]), {}).get("class_type", "").startswith("CLIPTextEncode"):
            return str(link[0])
    return None


def patch(wf: dict, prompt: str | None = None, negative: str | None = None, **knobs) -> dict:
    wf = copy.deepcopy(wf)
    for knob, value in knobs.items():
        if value is None:
            continue
        hit = False
        for node in wf.values():
            for name in KNOB_INPUTS[knob]:
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
    base = (base or os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")).rstrip("/")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with httpx.Client(base_url=base, timeout=60) as http:
        prompt_id = http.post("/prompt", json={"prompt": wf, "client_id": uuid.uuid4().hex}).raise_for_status().json()["prompt_id"]
        deadline = time.time() + timeout
        while time.time() < deadline:
            history = http.get(f"/history/{prompt_id}").raise_for_status().json()
            if prompt_id in history:
                break
            time.sleep(1)
        else:
            raise TimeoutError(f"ComfyUI did not finish {prompt_id} in {timeout}s")
        saved = []
        for node_output in history[prompt_id].get("outputs", {}).values():
            for img in node_output.get("images", []):
                data = http.get("/view", params={"filename": img["filename"], "subfolder": img.get("subfolder", ""),
                                                 "type": img.get("type", "output")}).raise_for_status().content
                target = out_dir / img["filename"]
                target.write_bytes(data)
                saved.append(target)
        return saved
