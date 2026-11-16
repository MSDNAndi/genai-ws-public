"""Lab 1 · step 1 — your first call to a model.

What this shows: one chat request and its answer. The same code talks to Azure AI Foundry, the workshop gateway,
OpenAI, Ollama, LM Studio, vLLM ... — only three settings change: the URL, the key and the model name.
What to notice: the answer, plus the token counts and finish_reason that come back with it.
"""
import os

from dotenv import find_dotenv, load_dotenv
from pathlib import Path as _Path
from openai import OpenAI

# ---- 1. Settings: read labs/.env so no secret is written in the code ----
_here = _Path(globals().get("__file__", ".")).resolve()   # no __file__ in a notebook: start at the cwd
for _folder in [*_here.parents, _Path.cwd(), *_Path.cwd().parents]:
    if (_folder / ".env").is_file():   # every .env from this file upward: the nearest one wins,
        load_dotenv(_folder / ".env")  # so labs/.env or one .env at the repo root both work
BASE, KEY, MODEL = os.environ["GENAI_BASE_URL"], os.environ["GENAI_API_KEY"], os.environ["GENAI_MODEL"]
# The workshop gateway (and Foundry keys) expect the key in an "api-key" header, not only as a Bearer token.
HEADERS = {"api-key": KEY} if os.getenv("GENAI_KEY_HEADER", "api-key") == "api-key" else None

# ---- 2. The client: one object that knows where to send requests ----
client = OpenAI(base_url=BASE, api_key=KEY, default_headers=HEADERS)
# Optional "think less" knob (GENAI_REASONING_EFFORT=low). Only sent when set; the workshop gateway drops it for
# models that don't support it, so switching GENAI_MODEL needs no other change.
EXTRA = {"reasoning_effort": os.environ["GENAI_REASONING_EFFORT"]} if os.getenv("GENAI_REASONING_EFFORT") else {}

# ---- 3. The call: a list of messages in, one answer out ----
response = client.chat.completions.create(
    model=MODEL,
    **EXTRA,                                                     # adds reasoning_effort=... only if it was set
    messages=[
        {"role": "system", "content": "You are a concise assistant for a developer workshop."},   # how to behave
        {"role": "user", "content": "In two sentences: what is a token, and why should a developer care?"},  # the question
    ],
)

# ---- 4. What came back: the text, plus usage (what you pay for) and why it stopped ----
print(response.choices[0].message.content)                     # choices[0] = the first (usually only) answer
usage = response.usage
print(f"\n[{response.model}] prompt={usage.prompt_tokens} completion={usage.completion_tokens} "
      f"total={usage.total_tokens} tokens · finish_reason={response.choices[0].finish_reason}")
# finish_reason "stop" = the model finished; "length" = it ran out of tokens mid-answer.

# Try this:
#  1. Change the system prompt ("answer like a pirate", "answer in German") and run again.
#  2. print(response.model_dump_json(indent=2))  — look at everything that came back (ids, usage, filters...).
#  3. Set GENAI_MODEL=<another deployment> in labs/.env and compare.
