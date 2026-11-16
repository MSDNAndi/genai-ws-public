"""Try it · Segment 4, slide 180 — "the model hears you" (cloud version, NOT local).

On the instructor laptop Gemma 4 E4B takes the audio itself, offline. A codespace has no microphone and no GPU, so
this is the honest cloud stand-in in three blocks: (1) a TTS voice speaks your question -> out/question.wav,
(2) a transcription model turns that audio into text, (3) the chat model answers what it HEARD in one sentence.
Run (from labs/):  python try/s4_hear.py            or your own question:  python try/s4_hear.py "Why is the sky blue?"
"""
import os
import sys
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
question = " ".join(sys.argv[1:]) or "How many legs does a spider have, and why is it not an insect?"

# ---- 1. MOUTH: a voice speaks the question (stands in for you talking into a microphone) ----
Path("out").mkdir(exist_ok=True)
wav = Path("out/question.wav")
with client.audio.speech.with_streaming_response.create(
        model=os.getenv("GENAI_TTS_MODEL", "gpt-4o-mini-tts"), voice=os.getenv("TTS_VOICE", "coral"),
        input=question, response_format="wav") as r:
    r.stream_to_file(wav)
print(f"[mouth]  spoke the question -> {wav}  (click it in the Explorer to listen)")

# ---- 2. EARS: speech to text. Gemma 4 E4B does this inside the model; here it is a separate model ----
with wav.open("rb") as f:
    heard = client.audio.transcriptions.create(
        model=os.getenv("GENAI_TRANSCRIBE_MODEL", "gpt-4o-mini-transcribe"), file=f).text
print(f"[ears]   heard: {heard}")

# ---- 3. BRAIN: answer what was heard, not what was typed ----
answer = client.chat.completions.create(model=os.environ["GENAI_MODEL"], **EXTRA, messages=[
    {"role": "user", "content": f"Answer in one sentence: {heard}"}]).choices[0].message.content
print(f"[answer] {answer}")

# What to notice:
#  * Three models and three network calls here; a model with audio input (Gemma 4 E4B) does blocks 2+3 in one step.
#  * Compare "heard" with your question: punctuation and odd names are where speech-to-text slips.
