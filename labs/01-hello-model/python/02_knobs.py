"""Lab 1 · step 2 — the sampling knobs: temperature, top_p, seed ... and the models that ignore them.

Reasoning models (gpt-5 family, o-series, many "thinking" models) fix temperature/top_p at their defaults and use
`reasoning_effort` instead. So this script asks the model first and falls back gracefully.
Tip: run it once with GENAI_MODEL=gpt-5-mini and once with GENAI_MODEL=$GENAI_MODEL_2 (e.g. DeepSeek-V3.2) or Ollama.
"""
import os
import time

from dotenv import find_dotenv, load_dotenv
from pathlib import Path as _Path
from openai import BadRequestError, OpenAI

_here = _Path(globals().get("__file__", ".")).resolve()   # no __file__ in a notebook: start at the cwd
for _folder in [*_here.parents, _Path.cwd(), *_Path.cwd().parents]:
    if (_folder / ".env").is_file():   # every .env from this file upward: the nearest one wins,
        load_dotenv(_folder / ".env")  # so labs/.env or one .env at the repo root both work
BASE, KEY, MODEL = os.environ["GENAI_BASE_URL"], os.environ["GENAI_API_KEY"], os.environ["GENAI_MODEL"]
HEADERS = {"api-key": KEY} if os.getenv("GENAI_KEY_HEADER", "api-key") == "api-key" else None
client = OpenAI(base_url=BASE, api_key=KEY, default_headers=HEADERS)
# local "thinking" models: OLLAMA-style reasoning_effort=none keeps this fast (the knob experiment itself is below)
EXTRA = {"reasoning_effort": "none"} if os.getenv("GENAI_REASONING_EFFORT") == "none" else {}

PROMPT = "Invent a name for a coffee shop run by robots. Answer with the name only."


def ask(**knobs) -> str:
    r = client.chat.completions.create(model=MODEL, messages=[{"role": "user", "content": PROMPT}], **EXTRA, **knobs)
    return (r.choices[0].message.content or "").strip()


try:
    for t in (0.0, 1.0, 1.6):
        print(f"temperature={t}: {[ask(temperature=t) for _ in range(3)]}")
    print(f"temperature=1.0, top_p=0.1: {[ask(temperature=1.0, top_p=0.1) for _ in range(3)]}")
    print(f"temperature=1.0, seed=42 (best effort!): {[ask(temperature=1.0, seed=42) for _ in range(3)]}")
except BadRequestError as e:
    print(f"'{MODEL}' rejected a sampling knob -> it is probably a reasoning model.\n  {str(e)[:200]}")
    print("Reasoning models expose a different knob: reasoning_effort (how long they think).")
    for effort in ("minimal", "low", "high"):
        t0 = time.perf_counter()
        try:
            r = client.chat.completions.create(model=MODEL, reasoning_effort=effort,
                                               messages=[{"role": "user", "content": "Is 1001 prime? One line."}])
        except BadRequestError as e2:
            print(f"  reasoning_effort={effort}: not supported here ({str(e2)[:80]})")
            continue
        u = r.usage
        hidden = getattr(getattr(u, "completion_tokens_details", None), "reasoning_tokens", None)
        print(f"  reasoning_effort={effort:<7} {time.perf_counter() - t0:5.1f}s  completion={u.completion_tokens} "
              f"(reasoning={hidden})  -> {(r.choices[0].message.content or '').strip()[:60]}")

# What to notice:
#  * temperature 0 is "mostly the same", not "guaranteed identical"; seed is best-effort on most providers.
#  * top_p=0.1 narrows the choice to the few most likely tokens — similar effect to a low temperature.
#  * reasoning tokens are billed even though you never see them.
