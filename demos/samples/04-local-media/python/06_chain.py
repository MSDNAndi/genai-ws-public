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
# # 06 - Chain: LLM, image, voice
#
# Lab 4 · stretch — the magic sauce is the pipeline: LLM -> image -> voice, each block swappable.
#
# 1. the chat model writes an image prompt and a one-line narration (structured output)
# 2. the image comes from ComfyUI (if COMFYUI_URL + a workflow are given) or from the cloud image model
# 3. the narration is spoken (step 5's endpoint)
# 4. out/chain.html shows the image and plays the audio
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
import argparse
import base64
import html
import os
from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from pathlib import Path as _Path
from openai import OpenAI
from pydantic import BaseModel

_here = _Path(globals().get("__file__", ".")).resolve()   # no __file__ in a notebook: start at the cwd
for _folder in [*_here.parents, _Path.cwd(), *_Path.cwd().parents]:
    if (_folder / ".env").is_file():   # every .env from this file upward: the nearest one wins,
        load_dotenv(_folder / ".env")  # so labs/.env or one .env at the repo root both work
KEY = os.environ["GENAI_API_KEY"]
HEADERS = {"api-key": KEY} if os.getenv("GENAI_KEY_HEADER", "api-key") == "api-key" else None
EXTRA = {"reasoning_effort": os.environ["GENAI_REASONING_EFFORT"]} if os.getenv("GENAI_REASONING_EFFORT") else {}
cloud = OpenAI(base_url=os.environ["GENAI_BASE_URL"], api_key=KEY, default_headers=HEADERS, timeout=300)

ap = argparse.ArgumentParser()
ap.add_argument("--topic", default="a drone delivering the last parcel of the day")
ap.add_argument("--workflow", help="ComfyUI API workflow; omit to use the cloud image model")
a = ap.parse_args()


class Scene(BaseModel):
    image_prompt: str
    narration: str


scene = cloud.chat.completions.parse(model=os.environ["GENAI_MODEL"], response_format=Scene, **EXTRA, messages=[
    {"role": "system", "content": "You write a vivid image prompt (max 40 words) and a one-sentence narration."},
    {"role": "user", "content": a.topic}]).choices[0].message.parsed
print("image prompt:", scene.image_prompt, "\nnarration:  ", scene.narration)

out = Path("out")
out.mkdir(exist_ok=True)
if a.workflow:
    import comfy
    image_path = comfy.run(comfy.patch(comfy.load(a.workflow), prompt=scene.image_prompt, seed=42), out)[0]
else:
    img = cloud.images.generate(model=os.getenv("GENAI_IMAGE_MODEL", "gpt-image-1-mini"), prompt=scene.image_prompt,
                                size="1024x1024", quality="low")
    image_path = out / "chain.png"
    image_path.write_bytes(base64.b64decode(img.data[0].b64_json))

with cloud.audio.speech.with_streaming_response.create(model=os.getenv("GENAI_TTS_MODEL", "gpt-4o-mini-tts"),
                                                       voice="alloy", input=scene.narration, response_format="wav") as r:
    r.stream_to_file(out / "chain.wav")

(out / "chain.html").write_text(f"""<!doctype html><meta charset="utf-8"><title>chain</title>
<body style="font-family:sans-serif;max-width:720px;margin:2rem auto"><img src="{image_path.name}" style="width:100%">
<p>{html.escape(scene.narration)}</p><audio controls autoplay src="chain.wav"></audio>
<p style="color:#888">prompt: {html.escape(scene.image_prompt)}</p></body>""", encoding="utf-8")
print(f"open {out / 'chain.html'}")
