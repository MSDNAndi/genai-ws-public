# /// script
# requires-python = ">=3.12"
# dependencies = ["genaiclass"]
#
# [tool.uv.sources]
# genaiclass = { path = "../../../shared/python", editable = true }
# ///
# %% [markdown]
# # 07 - One script, five providers
#
# The point of the whole workshop in 40 lines: the code below never changes. Only
# a base URL, a key and a model name change. Frontier cloud model, a Chinese open
# model through a router, and something on your own laptop all answer the same
# function call.
#
# ```bash
# uv run 07_five_providers.py                          # every profile that is configured
# uv run 07_five_providers.py mock ollama openrouter   # or name them
# ```

# %%
import sys
import time

from genaiclass import get_profile, list_profiles, make_client

PROMPT = "In one sentence: what is the difference between a token and a word?"

requested = [a for a in sys.argv[1:] if not a.startswith("-")]
names = requested or list(list_profiles())

# %% [markdown]
# ## Run the same request against each one
#
# Profiles that are not configured (no key, no local runner listening) are
# skipped with a reason rather than crashing the comparison.

# %%
rows: list[tuple[str, str, float, str]] = []

for name in names:
    profile = get_profile(name)
    if profile.missing():
        print(f"- {name:<14} skipped ({', '.join(profile.missing())} not set)")
        continue

    started = time.perf_counter()
    try:
        response = make_client(profile).chat.completions.create(
            model=profile.model,
            messages=[{"role": "user", "content": PROMPT}],
        )
    except Exception as error:
        print(f"- {name:<14} unreachable ({type(error).__name__})")
        continue

    elapsed = time.perf_counter() - started
    answer = (response.choices[0].message.content or "").strip().replace("\n", " ")
    tokens = response.usage.total_tokens if response.usage else 0
    rows.append((name, profile.model, elapsed, answer))
    print(f"\n### {name} - {profile.model}  ({elapsed:.1f}s, {tokens} tokens)")
    print(answer)

# %%
print("\n" + "=" * 72)
for name, model, elapsed, answer in rows:
    print(f"{name:<14} {model:<28} {elapsed:6.1f}s  {answer[:60]}...")

# %% [markdown]
# ## What to notice
#
# * **Latency varies more than quality** for a question this easy. The expensive
#   model is not obviously better here - pick per task, not per brand.
# * **The local model is not embarrassing.** That is the 2026 story: the gap that
#   matters for most application work is much smaller than the leaderboards suggest.
# * **Only configuration changed.** No SDK swap, no rewrite. This is what
#   "portability" buys you: the ability to leave.
#
# The same trick is what a gateway does at scale - APIM in front of Foundry,
# LiteLLM, OpenRouter. You keep one client and move the decision into config.
