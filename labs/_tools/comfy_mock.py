#!/usr/bin/env python3
"""comfy_mock.py - a stand-in for ComfyUI's HTTP API (POST /prompt, GET /history/<id>, GET /view, GET /system_stats)
so the Lab 4 scripts can be tested without a GPU. Each "render" is a flat image whose colour depends on the knobs and a
caption listing them - enough to see that seed/cfg/steps/prompt really reached the graph.

    python labs/_tools/comfy_mock.py 8188        # then COMFYUI_URL=http://127.0.0.1:8188
"""
import io
import json
import sys
import uuid
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from PIL import Image, ImageDraw

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8188
JOBS: dict[str, dict] = {}
IMAGES: dict[str, bytes] = {}


def render(wf: dict) -> bytes:
    knobs, prompt = {}, ""
    for node in wf.values():
        inputs = node.get("inputs", {})
        for name in ("seed", "noise_seed", "steps", "cfg", "guidance", "denoise", "width", "height"):
            if name in inputs and not isinstance(inputs[name], list):
                knobs[name] = inputs[name]
        if node.get("class_type", "").startswith("CLIPTextEncode") and not prompt:
            prompt = str(inputs.get("text", ""))
    h = zlib.crc32(json.dumps(knobs, sort_keys=True).encode() + prompt.encode())
    img = Image.new("RGB", (256, 256), (h & 255, (h >> 8) & 255, (h >> 16) & 255))
    d = ImageDraw.Draw(img)
    for i, line in enumerate([f"{k}={v}" for k, v in knobs.items()] + [prompt[:36]]):
        d.text((8, 8 + 14 * i), line, fill="white")
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _json(self, obj, code=200):
        data = json.dumps(obj).encode()
        self.send_response(code); self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data))); self.end_headers(); self.wfile.write(data)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("content-length", 0))) or b"{}")
        if urlparse(self.path).path == "/prompt":
            pid = uuid.uuid4().hex
            name = f"mock_{pid[:8]}.png"
            IMAGES[name] = render(body["prompt"])
            JOBS[pid] = {"outputs": {"9": {"images": [{"filename": name, "subfolder": "", "type": "output"}]}},
                         "status": {"status_str": "success", "completed": True}}
            return self._json({"prompt_id": pid, "number": len(JOBS), "node_errors": {}})
        self._json({"error": "not found"}, 404)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path.startswith("/history/"):
            pid = url.path.rsplit("/", 1)[-1]
            return self._json({pid: JOBS[pid]} if pid in JOBS else {})
        if url.path == "/view":
            data = IMAGES.get(parse_qs(url.query).get("filename", [""])[0])
            if data is None:
                return self._json({"error": "no such image"}, 404)
            self.send_response(200); self.send_header("content-type", "image/png")
            self.send_header("content-length", str(len(data))); self.end_headers(); self.wfile.write(data)
            return
        if url.path == "/system_stats":
            return self._json({"system": {"comfyui_version": "mock"}, "devices": []})
        self._json({"error": "not found"}, 404)


if __name__ == "__main__":
    print(f"ComfyUI mock on http://127.0.0.1:{PORT}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
