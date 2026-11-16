"""Try it · Segment 4, slide 223 — a song about today (cloud version: spoken, not sung).

Block 1 is Lab 1 code: one chat call turns today's agenda into short tagged lyrics ([verse] / [chorus]).
Block 2: on the instructor laptop ACE-Step 1.5 SINGS them on a GPU. Here gpt-4o-mini-tts PERFORMS them - a speaking
voice with rhythm and attitude from an instructions prompt. Same file chain: out/lyrics.txt -> out/song.wav.
Run (from labs/):  python try/s4_song.py            or:  python try/s4_song.py --tone "a slow, gravelly blues singer"
"""
import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# ---- Settings exactly like the labs: every .env from here upward (labs/.env), real environment variables win ----
for folder in [*Path(__file__).resolve().parents, Path.cwd(), *Path.cwd().parents]:
    if (folder / ".env").is_file():
        load_dotenv(folder / ".env")
KEY = os.environ["GENAI_API_KEY"]
HEADERS = {"api-key": KEY} if os.getenv("GENAI_KEY_HEADER", "api-key") == "api-key" else None
client = OpenAI(base_url=os.environ["GENAI_BASE_URL"], api_key=KEY, default_headers=HEADERS)
EXTRA = {"reasoning_effort": os.environ["GENAI_REASONING_EFFORT"]} if os.getenv("GENAI_REASONING_EFFORT") else {}

ap = argparse.ArgumentParser()
ap.add_argument("--tone", default="an upbeat pop singer on stage: rhythmic and bouncy, stretch the chorus words, "
                                  "almost singing, big energy on the last line")
ap.add_argument("--voice", default=os.getenv("TTS_VOICE", "ballad"))
a = ap.parse_args()

AGENDA = ["Segment 1: hello model - one API call, the knobs, structured output, the tool loop",
          "Segment 2: RAG and MCP - your own documents and tools for the model",
          "Segment 3: agents - loops, guards, many agents talking to each other",
          "Segment 4: local models and media - your laptop, images, voices, music"]

# ---- Block 1: LYRICS - one chat call, exactly like Lab 1 ----
lyrics = client.chat.completions.create(model=os.environ["GENAI_MODEL"], **EXTRA, messages=[
    {"role": "system", "content": "You write short, catchy song lyrics. Output only the lyrics."},
    {"role": "user", "content": "Write a song about this workshop day. Use the tags [verse], [chorus], [verse], "
                                "[chorus]; max 4 short lines per part; simple rhymes.\nAgenda:\n" + "\n".join(AGENDA)},
]).choices[0].message.content.strip()
Path("out").mkdir(exist_ok=True)
Path("out/lyrics.txt").write_text(lyrics, encoding="utf-8")
print(lyrics, "\n\n-> out/lyrics.txt")

# ---- Block 2: VOICE - tags guide a singing model; a speaking voice would read them out, so we drop them ----
spoken = "\n".join(line for line in lyrics.splitlines() if not line.strip().startswith("["))
with client.audio.speech.with_streaming_response.create(
        model=os.getenv("GENAI_TTS_MODEL", "gpt-4o-mini-tts"), voice=a.voice, input=spoken,
        instructions=a.tone, response_format="wav") as r:      # instructions = HOW to speak (gpt-4o-mini-tts)
    r.stream_to_file("out/song.wav")

# ---- Craft principle #1: keep the recipe next to the file (ACE-Step would log its seed here, too) ----
recipe = {"writer": os.environ["GENAI_MODEL"], "voice": a.voice, "tone": a.tone, "lyrics": "lyrics.txt"}
Path("out/song.json").write_text(json.dumps(recipe, indent=2), encoding="utf-8")
print("-> out/song.wav (spoken, not sung) + out/song.json - click the .wav in the Explorer to listen")

# What to notice:
#  * Change only --tone and run again: same words, a different performance - the voice prompt is a knob.
#  * Lyrics are plain text in a file, so the next stage (a singer, a video model) can be swapped without touching block 1.
