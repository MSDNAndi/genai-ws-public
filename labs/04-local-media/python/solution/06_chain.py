"""Lab 4 · step 6 — mix and match: the magic sauce is the pipeline. LLM -> image -> voice (-> ears), each block swappable.

What this shows: steps 4 and 5 chained together, with a chat model in front. Each block is one switch on the command
line, so you can swap ONE block per run and compare. What to notice: which block changes the result most, and which
one is slow (seconds per block are printed and shown on every card).

1. WRITER  a chat model writes an image prompt and a one-line narration (structured output, Lab 1)   --writer
2. IMAGE   the cloud image model, or ComfyUI (--workflow ...), or skip it                              --image / --workflow
3. VOICE   the narration is spoken (step 5's endpoint), with a voice and a speaking style            --voice / --tone
4. EARS    (--check) a transcription model listens to the audio: did the words survive?             TODO 1
Every run is kept: out/chain.html shows all runs side by side, newest first, with the recipe and timings of each.
Images are limited to 3 per minute per key: wait between runs, or use --image skip.

    python 06_chain.py                                         # baseline: GENAI_MODEL + gpt-image-1-mini + alloy
    python 06_chain.py --writer grok-4-1-fast-non-reasoning    # swap ONE block, compare in out/chain.html
    python 06_chain.py --writer-only --writer DeepSeek-V4.1-Flash-1017   # text only: no image/voice quota used
"""
import argparse
import base64
import html
import json
import os
import re
import time
from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from pathlib import Path as _Path
from openai import OpenAI, OpenAIError, RateLimitError
from pydantic import BaseModel, ValidationError

_here = _Path(globals().get("__file__", ".")).resolve()   # no __file__ in a notebook: start at the cwd
for _folder in [*_here.parents, _Path.cwd(), *_Path.cwd().parents]:
    if (_folder / ".env").is_file():   # every .env from this file upward: the nearest one wins,
        load_dotenv(_folder / ".env")  # so labs/.env or one .env at the repo root both work

# One client for every cloud block (chat, image, speech, transcription): same endpoint, same key.
KEY = os.environ["GENAI_API_KEY"]
HEADERS = {"api-key": KEY} if os.getenv("GENAI_KEY_HEADER", "api-key") == "api-key" else None
cloud = OpenAI(base_url=os.environ["GENAI_BASE_URL"], api_key=KEY, default_headers=HEADERS, timeout=300)

# The switches. Every block is a knob: command line > environment variable (labs/.env) > default
ap = argparse.ArgumentParser(description="LLM -> image -> voice, each block swappable")
ap.add_argument("--topic", default="a drone delivering the last parcel of the day")
ap.add_argument("--writer", default=os.getenv("CHAIN_WRITER", os.getenv("GENAI_MODEL", "gpt-5-nano")),
                help="any chat model on the endpoint, e.g. gpt-5-mini, grok-4-1-fast-non-reasoning")
ap.add_argument("--style", default="", help="extra direction for the writer, e.g. 'film noir' or 'for kids'")
ap.add_argument("--image", default=os.getenv("GENAI_IMAGE_MODEL", "gpt-image-1-mini"),
                help="cloud image model, or 'skip' (ignored when --workflow is given)")
ap.add_argument("--workflow", help="ComfyUI API workflow instead of the cloud, e.g. ../comfyui_workflows/01_txt2img_sdxl.json")
ap.add_argument("--voice", default=os.getenv("TTS_VOICE", "alloy"),
                help="alloy, ash, ballad, coral, echo, fable, nova, onyx, sage, shimmer, verse")
ap.add_argument("--tone", default="", help="how to speak (gpt-4o-mini-tts), e.g. 'a whispering nature documentary'")
ap.add_argument("--tts-model", default=os.getenv("GENAI_TTS_MODEL", "gpt-4o-mini-tts"))
ap.add_argument("--writer-only", action="store_true", help="stop after the writer: compare writers without media quota")
ap.add_argument("--check", action="store_true", help="4th block: transcribe the audio back and compare (TODO 1)")
a = ap.parse_args()


# The writer must return exactly these two fields (structured output, as in Lab 1).
class Scene(BaseModel):
    image_prompt: str
    narration: str


def reasoning_args(model: str) -> dict:
    """reasoning_effort only for the models that understand it (gpt-5*, gpt-oss); others answer 400.
    (The workshop gateway also strips it for those models - this keeps your own endpoint working, too.)"""
    if re.match(r"(gpt-5|gpt-oss|o\d)", model, re.I):
        return {"reasoning_effort": os.getenv("GENAI_REASONING_EFFORT", "low")}
    return {}


def write_scene(model: str) -> tuple[Scene, str]:
    """Ask the writer model for a Scene. Not every vendor supports every feature, so we try three ways, best first:
    1. structured output (the API enforces our two fields)  2. JSON mode (any valid JSON)  3. plain text with JSON in it."""
    system = ("You write a vivid image prompt (max 40 words) and a one-sentence narration (max 25 words) for the topic. "
              + (f"Style: {a.style}. " if a.style else ""))
    messages = [{"role": "system", "content": system}, {"role": "user", "content": a.topic}]
    try:
        r = cloud.chat.completions.parse(model=model, response_format=Scene, messages=messages, **reasoning_args(model))
        if r.choices[0].message.parsed:
            return r.choices[0].message.parsed, "structured output"
    except (OpenAIError, ValidationError) as e:
        if getattr(e, "status_code", 0) in (401, 403, 404, 429):
            raise   # wrong key / model not allowed / rate limit: a fallback will not help
        print(f"  ({model}: structured output failed - {type(e).__name__}; trying JSON mode)")
    # Fallbacks 2 and 3: describe the JSON in the prompt instead, then pull the {...} out of the answer text.
    messages[0]["content"] += 'Answer ONLY with JSON: {"image_prompt": "...", "narration": "..."}'
    for mode in ({"response_format": {"type": "json_object"}}, {}):
        try:
            text = cloud.chat.completions.create(model=model, messages=messages, **mode,
                                                 **reasoning_args(model)).choices[0].message.content or ""
            return Scene.model_validate_json(re.search(r"\{.*\}", text, re.S).group(0)), \
                "JSON mode" if mode else "plain text + JSON"
        except (OpenAIError, ValidationError, AttributeError) as e:
            if getattr(e, "status_code", 0) in (401, 403, 404, 429):
                raise
            last = e
    raise SystemExit(f"{model} could not produce the two fields ({type(last).__name__}). Try another --writer.")


# --- the run: one "recipe" dict collects what each block did; it is saved as out/chain_<run>.json at the end ---------
out = Path("out")
out.mkdir(exist_ok=True)
run_id = time.strftime("%Y%m%d-%H%M%S")
recipe = {"run": run_id, "topic": a.topic, "writer": a.writer, "style": a.style, "timings_s": {}}
t = time.perf_counter()

# --- block 1: WRITER - a chat model turns the topic into an image prompt + a narration ---------------------------
try:
    scene, how = write_scene(a.writer)
except OpenAIError as e:   # 403 = not one of the workshop's models: the message lists them
    raise SystemExit(f"[writer] {a.writer}: {getattr(e, 'message', e)}")
recipe["timings_s"]["writer"] = round(time.perf_counter() - t, 1)
recipe.update(writer_mode=how, image_prompt=scene.image_prompt, narration=scene.narration)
print(f"[writer] {a.writer} ({how}, {recipe['timings_s']['writer']}s)\n  image prompt: {scene.image_prompt}"
      f"\n  narration:    {scene.narration}")
if a.writer_only:          # --writer-only: compare writers without spending image or voice quota
    raise SystemExit(0)

# --- block 2: IMAGE - ComfyUI (--workflow), the cloud image model (step 4), or nothing (--image skip) -------------
t = time.perf_counter()
image_file = None
if a.workflow:
    import comfy   # only needed for the ComfyUI path; seed fixed at 42 so reruns are comparable
    recipe["image"] = f"ComfyUI {Path(a.workflow).name} seed 42"
    src = comfy.run(comfy.patch(comfy.load(a.workflow), prompt=scene.image_prompt, seed=42), out)[0]
    image_file = out / f"chain_{run_id}{src.suffix}"
    src.replace(image_file)
elif a.image != "skip":
    recipe["image"] = a.image
    try:
        img = cloud.images.generate(model=a.image, prompt=scene.image_prompt, size="1024x1024", quality="low")
        image_file = out / f"chain_{run_id}.png"
        image_file.write_bytes(base64.b64decode(img.data[0].b64_json))
    except RateLimitError:
        print("[image] rate limit (3 images per minute per key) - this run has no picture; wait a minute,"
              " or use --image skip / --workflow while you compare writers and voices")
else:
    recipe["image"] = "skipped"
recipe["timings_s"]["image"] = round(time.perf_counter() - t, 1)
print(f"[image]  {recipe['image']} ({recipe['timings_s']['image']}s) -> {image_file or '-'}")

# --- block 3: VOICE - the narration is spoken (step 5) ---------------------------------------------------------
t = time.perf_counter()
audio_file = out / f"chain_{run_id}.wav"
speech = {"model": a.tts_model, "voice": a.voice, "input": scene.narration, "response_format": "wav"}
if a.tone:
    speech["instructions"] = a.tone   # gpt-4o-mini-tts takes speaking directions; older TTS models ignore/reject it
with cloud.audio.speech.with_streaming_response.create(**speech) as r:
    r.stream_to_file(audio_file)
recipe.update(voice=f"{a.tts_model} / {a.voice}" + (f" / {a.tone}" if a.tone else ""))
recipe["timings_s"]["voice"] = round(time.perf_counter() - t, 1)
print(f"[voice]  {recipe['voice']} ({recipe['timings_s']['voice']}s) -> {audio_file}")

# --- block 4 (optional, --check): EARS - a transcription model (speech to text) listens back --------------------
if a.check:
    t = time.perf_counter()
    try:
        # >>> TODO 1: transcribe audio_file with os.getenv("GENAI_TRANSCRIBE_MODEL", "gpt-4o-mini-transcribe") (cloud.audio.transcriptions.create) and store the text in recipe["heard"]
        with audio_file.open("rb") as f:
            recipe["heard"] = cloud.audio.transcriptions.create(
                model=os.getenv("GENAI_TRANSCRIBE_MODEL", "gpt-4o-mini-transcribe"), file=f).text
        # <<< TODO
    except OpenAIError as e:   # e.g. 404: this endpoint has no transcription model - the other blocks still count
        print(f"[ears]   transcription failed ({getattr(e, 'status_code', type(e).__name__)}) - skipping the check")
    else:
        recipe["timings_s"]["ears"] = round(time.perf_counter() - t, 1)
        # simple test: how many of the written words were heard again?
        said, heard = (re.findall(r"[a-z0-9']+", s.lower()) for s in (scene.narration, recipe["heard"]))
        recipe["words_match"] = f"{sum(w in heard for w in said)}/{len(said)}"
        print(f"[ears]   heard: {recipe['heard']}  ({recipe['words_match']} words, {recipe['timings_s']['ears']}s)")

# --- the gallery: save this run's recipe, then rebuild out/chain.html from ALL saved recipes, newest first --------
recipe.update(image_file=image_file.name if image_file else None, audio_file=audio_file.name)
(out / f"chain_{run_id}.json").write_text(json.dumps(recipe, indent=2), encoding="utf-8")
cards = []
for p in sorted(out.glob("chain_*.json"), reverse=True):
    r = json.loads(p.read_text(encoding="utf-8"))
    e = lambda k: html.escape(str(r.get(k) or "-"))   # noqa: E731   (escape: model text must not break the HTML)
    img = f'<img src="{e("image_file")}">' if r.get("image_file") else '<div class="noimg">no image</div>'
    heard = f'<p class="k">heard: {e("heard")} ({e("words_match")} words)</p>' if r.get("heard") else ""
    cards.append(f"""<div class="card">{img}<p class="n">{e("narration")}</p>
<audio controls preload="none" src="{e("audio_file")}"></audio>{heard}
<p class="k"><b>writer</b> {e("writer")} ({e("writer_mode")}){" · style " + e("style") if r.get("style") else ""}<br>
<b>image</b> {e("image")}<br><b>voice</b> {e("voice")}<br><b>seconds</b> {e("timings_s")}<br>
<b>prompt</b> {e("image_prompt")}<br><b>run</b> {e("run")} · {e("topic")}</p></div>""")
(out / "chain.html").write_text("""<!doctype html><meta charset="utf-8"><title>Lab 4 · mix and match</title>
<style>body{font-family:sans-serif;margin:1.5rem;background:#fafafa}h1{font-size:1.3rem}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:1rem}
.card{background:#fff;border:1px solid #ddd;border-radius:8px;padding:.8rem}.card img,.noimg{width:100%;aspect-ratio:1;
object-fit:cover;border-radius:4px;background:#eee;display:flex;align-items:center;justify-content:center;color:#999}
.n{font-size:1.05rem}.k{color:#666;font-size:.8rem}audio{width:100%}</style>
<h1>Lab 4 · mix and match — newest run first (reload after each run)</h1><div class="grid">"""
                                + "\n".join(cards) + "</div>", encoding="utf-8")
print(f"{len(cards)} run(s) in {out / 'chain.html'} - view it: python -m http.server 8000 -d out, then open /chain.html")
