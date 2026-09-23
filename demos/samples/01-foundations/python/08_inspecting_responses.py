# /// script
# requires-python = ">=3.12"
# dependencies = ["genaiclass"]
#
# [tool.uv.sources]
# genaiclass = { path = "../../../shared/python", editable = true }
# ///
# %% [markdown]
# # 08 - What actually comes back
#
# Half of the original workshop happened here: type `completion` into a cell,
# expand the tree, and *see* that a chat response is a small object graph with
# ids, a finish reason, token counts, content parts, filter results and a raw
# HTTP body underneath.
#
# Scripts do not print an expandable tree by themselves, so this repo ships the
# view instead of relying on the runner:
#
# * `dump(obj)`   - indented tree in the terminal
# * `inspect(obj)` - collapsible HTML page in your browser
# * `raw_json(..)` - the wire format, before the SDK typed anything
#
# In a notebook (see `notebooks/`, or `tools/to_notebook.py`) just end a cell
# with the object and the kernel renders it - that path still works too.
#
# ```bash
# uv run 08_inspecting_responses.py --profile mock
# GENAI_NO_BROWSER=1 uv run 08_inspecting_responses.py --profile mock   # no popup
# ```

# %%
from genaiclass import banner, dump, get_profile, inspect, make_client, raw_json

profile = get_profile()
client = make_client(profile)
print(banner(profile))

# %% [markdown]
# ## 1. Keep the raw HTTP response
#
# `with_raw_response` gives you headers and body as they arrived, and `.parse()`
# then produces the typed object. Two things worth showing students live: the
# rate-limit headers (this is where a 429 is explained) and the fact that the
# SDK is a thin typing layer over plain JSON.

# %%
raw = client.chat.completions.with_raw_response.create(
    model=profile.model,
    messages=[{"role": "user", "content": "Name two blue things."}],
)

interesting = (
    # OpenAI / Foundry
    "x-ratelimit-remaining-tokens", "x-ratelimit-remaining-requests",
    "x-request-id", "apim-request-id",
    # the workshop APIM gateway's llm-token-limit policy emits these three:
    # your remaining budget this minute, for the day, and what this call cost
    "x-remaining-tokens", "x-remaining-quota-tokens", "x-tokens-consumed",
    "content-type",
)
print("status:", raw.http_response.status_code)
for header in interesting:
    if header in raw.http_response.headers:
        print(f"  {header}: {raw.http_response.headers[header]}")

print("\n--- raw body -------------------------------------------------")
print(raw_json(raw)[:900])

# %%
completion = raw.parse()

# %% [markdown]
# ## 2. The typed object, as a tree
#
# This is the notebook view, printed. Note what is there beyond the text: the
# `finish_reason`, the token accounting split into prompt/completion (and, on
# reasoning models, `completion_tokens_details.reasoning_tokens`, which is where
# surprise bills come from), and `content_filter_results` on Azure/Foundry.

# %%
dump(completion, title="ChatCompletion")

# %% [markdown]
# ## 3. Drill down interactively
#
# `inspect` writes a self-contained HTML page with collapsible nodes and opens
# it. Set `GENAI_NO_BROWSER=1` to only write the file - handy when projecting, or
# in CI.

# %%
path = inspect(completion, title="ChatCompletion - expand me", open_levels=3)
print(f"wrote {path}")

# %% [markdown]
# ## 4. The pieces worth naming out loud
#
# | Field | Why you care |
# |---|---|
# | `choices[0].finish_reason` | `stop` vs `length` vs `tool_calls` vs `content_filter` - your control flow |
# | `usage.prompt_tokens` | grows with every turn; this is why long chats get expensive |
# | `usage.completion_tokens_details.reasoning_tokens` | hidden thinking you are billed for |
# | `usage.prompt_tokens_details.cached_tokens` | prompt caching actually working |
# | `system_fingerprint` | the backend changed under you; seeds are no longer comparable |
# | `content_filter_results` | Azure/Foundry RAI verdicts per category |
# | `model` | what you *got*, which is not always what you asked for (routers) |
#
# ## The same trick anywhere
#
# `dump` and `inspect` take any object, not just SDK responses - a tool-call
# argument, an agent run result, an MCP payload. When something behaves oddly
# three layers into a framework, printing the actual object is usually faster
# than reading the framework's source.
