# /// script
# requires-python = ">=3.12"
# dependencies = ["genaiclass"]
#
# [tool.uv.sources]
# genaiclass = { path = "../../../shared/python", editable = true }
# ///
# %% [markdown]
# # 02 - The knobs you actually control
#
# Sampling happens *after* the model has produced a probability distribution over
# the next token. These parameters reshape that distribution - they do not make
# the model smarter, and they are the same everywhere.
#
# ```bash
# uv run 02_sampling_knobs.py --profile mock
# ```

# %%
import os
import sys

import openai
from genaiclass import banner, get_profile, make_client

profile = get_profile()
client = make_client(profile)
print(banner(profile))

# Reasoning models (gpt-5*, gpt-6*, o-series) accept only the default temperature and
# reject top_p. The knobs need a non-reasoning model: GENAI_SAMPLING_MODEL (gpt-4.1 on
# the workshop gateway, see .env.example), else the profile's default model.
MODEL = os.environ.get("GENAI_SAMPLING_MODEL") or profile.model
print(f"sampling model: {MODEL}")

PROMPT = "Invent a name for a coffee shop run by cats. Just the name."


def ask(**kwargs) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": PROMPT}],
        **kwargs,
    )
    return (response.choices[0].message.content or "").strip()


# %% [markdown]
# ## temperature: how flat the distribution gets
#
# 0 = always take the most likely token (repeatable-ish), higher = more of the
# tail becomes reachable. Above ~1.2 most models start producing noise.

# %%
try:
    for temperature in (0.0, 0.7, 1.4):
        print(f"temperature={temperature:<4} -> {ask(temperature=temperature)}")
except openai.BadRequestError as e:
    # The lesson, not a crash: this is exactly what a reasoning model answers.
    print()
    print(f"{MODEL} rejected the knob: {e.message[:160]}")
    print("Reasoning models fix temperature/top_p. Set GENAI_SAMPLING_MODEL to a non-reasoning")
    print("model (gpt-4.1, gpt-4o-mini, DeepSeek-V3.2 ...) in .env and run this again.")
    sys.exit(0)

# %% [markdown]
# ## top_p: nucleus sampling
#
# Keep the smallest set of tokens whose probabilities sum to `top_p`, sample from
# those. Change one of temperature/top_p, not both - they fight each other.

# %%
for top_p in (0.1, 1.0):
    print(f"top_p={top_p:<4} -> {ask(top_p=top_p)}")

# %% [markdown]
# ## max_tokens: the stop sign, not a summarizer
#
# The model is not told to be brief - it is cut off mid-sentence. Watch
# `finish_reason` go from `stop` to `length`. If you want short answers, *ask*
# for short answers.

# %%
truncated = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": "Explain the transformer architecture."}],
    max_completion_tokens=16,
)
print(f"finish_reason={truncated.choices[0].finish_reason!r}")
print(truncated.choices[0].message.content)

# %% [markdown]
# ## seed: best-effort reproducibility
#
# With the same seed, prompt and parameters most providers return the same text.
# "Best effort" is literal - a backend change invalidates it. Check
# `system_fingerprint` to see whether you are still on the same setup.

# %%
for attempt in (1, 2):
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": PROMPT}],
        temperature=1.0,
        seed=42,
    )
    print(f"run {attempt}: {response.choices[0].message.content!r} "
          f"(fingerprint={getattr(response, 'system_fingerprint', None)})")

# %% [markdown]
# ## What is *not* a sampling knob
#
# `reasoning_effort` (GPT-5, o-series, and the open reasoning models) buys extra
# hidden thinking tokens before the answer. It is a cost/latency/quality dial,
# billed as output tokens - a different room entirely from temperature.
# Same question, three efforts, on a REASONING model - GENAI_REASONING_MODEL (gpt-5-mini on the
# workshop gateway), independent of the default model: watch hidden tokens and time grow.

# %%
import time

PUZZLE = ("Three boxes are labelled 'apples', 'oranges' and 'mixed'; every label is wrong. "
          "You may take one fruit from one box. Which box do you pick from, and why? Two sentences.")
REASONING_MODEL = os.environ.get("GENAI_REASONING_MODEL") or profile.model
print(f"reasoning model: {REASONING_MODEL}")
for effort in ("minimal", "low", "high"):
    t0 = time.perf_counter()
    try:
        r = client.chat.completions.create(model=REASONING_MODEL, reasoning_effort=effort,
                                           messages=[{"role": "user", "content": PUZZLE}])
    except openai.BadRequestError as e:
        # non-reasoning models (gpt-4.1, the mock) have no such knob - say so and stop
        print(f"{REASONING_MODEL} has no reasoning_effort: {e.message[:100]}")
        break
    u = r.usage
    hidden = getattr(u.completion_tokens_details, "reasoning_tokens", None) if u.completion_tokens_details else None
    print(f"reasoning_effort={effort:<7} {time.perf_counter() - t0:5.1f}s  billed={u.completion_tokens:>4}  "
          f"hidden reasoning={hidden}  -> {(r.choices[0].message.content or '').strip()[:70]}")
