"""Lab 4 · step 5 — text to speech (TTS: the model reads text aloud).

What this shows: speech uses the same OpenAI-compatible client again, just a different call (`audio.speech`, which is
POST /audio/speech). We send a sentence and a voice name and save the answer as out/welcome.wav.
What to notice: we STREAM the audio straight into the file instead of holding it all in memory first.

Cloud (default): GENAI_TTS_MODEL (gpt-4o-mini-tts on the workshop endpoint). Local, optional: any OpenAI-compatible TTS
server - set TTS_BASE_URL, TTS_MODEL, TTS_VOICE (e.g. a Kokoro or Qwen3-TTS server; check its model/voice names).
"""
import os
import time
from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from pathlib import Path as _Path
from openai import OpenAI

# Load the settings file (labs/.env). Real environment variables win over the file.
_here = _Path(globals().get("__file__", ".")).resolve()   # no __file__ in a notebook: start at the cwd
for _folder in [*_here.parents, _Path.cwd(), *_Path.cwd().parents]:
    if (_folder / ".env").is_file():   # every .env from this file upward: the nearest one wins,
        load_dotenv(_folder / ".env")  # so labs/.env or one .env at the repo root both work

# Pick the speech server: a local one if TTS_BASE_URL is set, otherwise the workshop endpoint.
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
# The call: model + voice + text in, audio out. response_format picks the file type (wav, mp3, ...).
# >>> TODO 1: request speech for `text` with a voice (e.g. "alloy" or os.getenv("TTS_VOICE")) as WAV and save it to out/welcome.wav
Path("out").mkdir(exist_ok=True)
with client.audio.speech.with_streaming_response.create(model=model, voice=os.getenv("TTS_VOICE", "alloy"), input=text,
                                                        response_format="wav") as response:
    response.stream_to_file("out/welcome.wav")
# <<< TODO
print(f"out/welcome.wav ({Path('out/welcome.wav').stat().st_size / 1024:.0f} KB) in {time.perf_counter() - t0:.1f}s")
# Listen: click out/welcome.wav in the Explorer on the left - VS Code plays it.
