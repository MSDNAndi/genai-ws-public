"""Try it · Segment 1, slide 51 — what reasoning_effort costs, and who refuses a knob.

What this shows: one prompt sent three times to a reasoning model with reasoning_effort low / medium / high,
printing seconds, tokens (incl. the hidden reasoning tokens) and an estimated bill per call.
Before that it asks for temperature=0.2 — a reasoning model like gpt-5-nano refuses it with a 400.
Run (from labs/):  GENAI_MODEL=gpt-5-nano python try/s1_effort_cost.py
Prices: list price of gpt-5-nano in USD per 1M tokens; set GENAI_PRICE_IN / GENAI_PRICE_OUT for another model.
"""
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import BadRequestError, OpenAI

# ---- 1. Settings and client, exactly like the labs: labs/.env, real environment variables win ----
for folder in [*Path(__file__).resolve().parents, Path.cwd(), *Path.cwd().parents]:
    if (folder / ".env").is_file():
        load_dotenv(folder / ".env")    # load_dotenv never overwrites a variable that is already set
BASE, KEY, MODEL = os.environ["GENAI_BASE_URL"], os.environ["GENAI_API_KEY"], os.environ["GENAI_MODEL"]
HEADERS = {"api-key": KEY} if os.getenv("GENAI_KEY_HEADER", "api-key") == "api-key" else None
client = OpenAI(base_url=BASE, api_key=KEY, default_headers=HEADERS)
PRICE_IN = float(os.getenv("GENAI_PRICE_IN", "0.05"))     # USD per 1M input tokens  (gpt-5-nano list price)
PRICE_OUT = float(os.getenv("GENAI_PRICE_OUT", "0.40"))   # USD per 1M output tokens (reasoning tokens count as output)
PROMPT = [{"role": "user", "content": "Is 1001 prime? Answer in one line."}]

# ---- 2. Who refuses it: ask for a sampling knob that reasoning models lock ----
try:
    client.chat.completions.create(model=MODEL, messages=PROMPT, temperature=0.2)
    print(f"{MODEL} accepted temperature=0.2 -> it does not lock sampling knobs. The workshop gateway drops\n"
          f"  reasoning_effort for such models, so below expect hidden=0 at every level (prices shown are gpt-5-nano's).")
except BadRequestError as e:
    print(f"{MODEL} refused temperature=0.2 (400): {str(e)[:150]}")

# ---- 3. The experiment: the same prompt at three effort levels (this script sets the knob on purpose) ----
print(f"\n{'effort':<8}{'seconds':>8}{'prompt':>8}{'output':>8}{'hidden':>8}{'est. USD':>11}  answer")
for effort in ("low", "medium", "high"):
    t0 = time.perf_counter()
    try:
        r = client.chat.completions.create(model=MODEL, messages=PROMPT, reasoning_effort=effort)
    except BadRequestError as e:                        # some models only know some levels
        print(f"{effort:<8} not supported: {str(e)[:100]}")
        continue
    u = r.usage
    # reasoning_tokens = hidden "thinking"; they are already included in completion_tokens (and billed as output)
    hidden = getattr(getattr(u, "completion_tokens_details", None), "reasoning_tokens", None) or 0
    usd = (u.prompt_tokens * PRICE_IN + u.completion_tokens * PRICE_OUT) / 1_000_000
    answer = (r.choices[0].message.content or "").strip().replace("\n", " ")[:50]
    print(f"{effort:<8}{time.perf_counter() - t0:>8.1f}{u.prompt_tokens:>8}{u.completion_tokens:>8}{hidden:>8}"
          f"{usd:>11.6f}  {answer}")

# What to notice:
#  * same question, same answer, but "high" can think many times longer -> more seconds, more output tokens, bigger bill.
#  * you never see the hidden tokens, yet you pay for them as output tokens.
#  * multiply the per-call cost by a million calls a month: the effort level is a cost decision.
