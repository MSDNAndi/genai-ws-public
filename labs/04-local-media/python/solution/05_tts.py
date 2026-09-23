"""Lab 4 · step 5 — text to speech through the same OpenAI-compatible client: POST /audio/speech.

Cloud: GENAI_TTS_MODEL (e.g. gpt-4o-mini-tts on Foundry). Local: any OpenAI-compatible TTS server
(set TTS_BASE_URL, TTS_MODEL, TTS_VOICE — e.g. a Kokoro or Qwen3-TTS server; check your server's model/voice names).
"""
import os
import time
from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from pathlib import Path as _Path
from openai import OpenAI

_here = _Path(globals().get("__file__", ".")).resolve()   # no __file__ in a notebook: start at the cwd
for _folder in [*_here.parents, _Path.cwd(), *_Path.cwd().parents]:
    if (_folder / ".env").is_file():   # every .env from this file upward: the nearest one wins,
        load_dotenv(_folder / ".env")  # so labs/.env or one .env at the repo root both work
if os.getenv("TTS_BASE_URL"):
    client, model = OpenAI(base_url=os.environ["TTS_BASE_URL"], api_key="local"), os.environ["TTS_MODEL"]
else:
    key = os.environ["GENAI_API_KEY"]
    headers = {"api-key": key} if os.getenv("GENAI_KEY_HEADER", "api-key") == "api-key" else None
    client = OpenAI(base_url=os.environ["GENAI_BASE_URL"], api_key=key, default_headers=headers)
    model = os.getenv("GENAI_TTS_MODEL", "gpt-4o-mini-tts")

text = ("Welcome to segment four. Everything you built today also runs on your own machine - "
        "and now it can talk.")
t0 = time.perf_counter()
# >>> TODO 1: request speech for `text` with a voice (e.g. "alloy" or os.getenv("TTS_VOICE")) as WAV and save it to out/welcome.wav
Path("out").mkdir(exist_ok=True)
with client.audio.speech.with_streaming_response.create(model=model, voice=os.getenv("TTS_VOICE", "alloy"), input=text,
                                                        response_format="wav") as response:
    response.stream_to_file("out/welcome.wav")
# <<< TODO
print(f"out/welcome.wav ({Path('out/welcome.wav').stat().st_size / 1024:.0f} KB) in {time.perf_counter() - t0:.1f}s")
