"""Try it · Segment 1, slide 61 — one script, five providers.

What this shows: the same prompt and the same code sent to five models from five vendors
(OpenAI, DeepSeek, xAI, Meta, OpenAI open-weight), all behind the one workshop URL and your one key.
Only the model name changes. Run (from labs/):  python try/s1_five_providers.py
Other models? Pass them as arguments:  python try/s1_five_providers.py gpt-5-nano gpt-oss-120b
"""
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# ---- 1. Settings, exactly like the labs: labs/.env, real environment variables win ----
for folder in [*Path(__file__).resolve().parents, Path.cwd(), *Path.cwd().parents]:
    if (folder / ".env").is_file():
        load_dotenv(folder / ".env")    # load_dotenv never overwrites a variable that is already set
BASE, KEY = os.environ["GENAI_BASE_URL"], os.environ["GENAI_API_KEY"]
HEADERS = {"api-key": KEY} if os.getenv("GENAI_KEY_HEADER", "api-key") == "api-key" else None
# ONE client for all five: same URL, same key. max_retries=0 so a busy model is reported at once.
client = OpenAI(base_url=BASE, api_key=KEY, default_headers=HEADERS, timeout=120, max_retries=0)

# The thinking knob comes only from labs/.env (GENAI_REASONING_EFFORT); the workshop gateway
# drops it for models that would reject it (DeepSeek, grok, Llama ...), so one setting fits all.
EFFORT = os.getenv("GENAI_REASONING_EFFORT")
EXTRA = {"reasoning_effort": EFFORT} if EFFORT else {}

# ---- 2. The five targets: (vendor, deployment name) — the ONLY thing that differs ----
MODELS = [
    ("OpenAI", "gpt-5-nano"),
    ("DeepSeek", "DeepSeek-V4.1-Flash-1017"),
    ("xAI", "grok-4-1-fast-non-reasoning"),
    ("Meta", "Llama-4-Maverick-17B-128E-Instruct-FP8"),
    ("OpenAI open-weight", "gpt-oss-120b"),
]
if len(sys.argv) > 1:                                   # your own list from the command line
    MODELS = [("", m) for m in sys.argv[1:]]

PROMPT = "Explain retrieval-augmented generation to a developer in one sentence."

# ---- 3. Same call, every model: time it, count tokens, keep the answer ----
print(f"Prompt: {PROMPT}\n")
for vendor, model in MODELS:
    t0 = time.perf_counter()
    try:
        r = client.chat.completions.create(model=model, messages=[{"role": "user", "content": PROMPT}], **EXTRA)
    except Exception as e:                              # one failing model must not stop the comparison
        print(f"{model}  skipped ({type(e).__name__}: {str(e)[:100]})\n")
        continue
    seconds = time.perf_counter() - t0
    tokens = r.usage.completion_tokens if r.usage else "?"
    answer = (r.choices[0].message.content or "").strip().replace("\n", " ")
    print(f"{model}{f' ({vendor})' if vendor else ''}  ·  {seconds:.1f}s  ·  {tokens} tokens\n   {answer[:300]}\n")

# What to notice:
#  * identical code — only the model name changed, and you got five vendors.
#  * compare speed, length and style: "fast-non-reasoning" models answer quickly; reasoning ones spend hidden tokens.
#  * that one-line switch is what provider independence means.
