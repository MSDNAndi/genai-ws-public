# /// script
# requires-python = ">=3.12"
# dependencies = ["genaiclass"]
#
# [tool.uv.sources]
# genaiclass = { path = "../../../shared/python", editable = true }
# ///
# %% [markdown]
# # 01 - Hello, model
#
# The smallest useful call there is: a list of messages in, one message out.
# Everything later in this workshop is this call with more structure around it.
#
# Run it:
#
# ```bash
# uv run 01_hello_model.py                 # uses GENAI_PROFILE from .env
# uv run 01_hello_model.py --profile ollama
# ```

# %%
from genaiclass import banner, get_profile, make_client

profile = get_profile()
client = make_client(profile)
print(banner(profile))

# %% [markdown]
# ## The call
#
# `messages` is the whole conversation - the model is stateless, so *you* own the
# history. Roles: `system`/`developer` = standing instructions, `user` = the turn,
# `assistant` = what the model said last time.

# %%
response = client.chat.completions.create(
    model=profile.model,
    messages=[
        {"role": "system", "content": "You are a concise assistant. Answer in one sentence."},
        {"role": "user", "content": "Why is the sky blue?"},
    ],
)

print(response.choices[0].message.content)

# %% [markdown]
# ## What else came back
#
# Tokens are the unit you pay in, and `finish_reason` tells you *why* the model
# stopped - `stop` means it was done, `length` means you cut it off.

# %%
usage = response.usage
print(f"finish_reason : {response.choices[0].finish_reason}")
print(f"model         : {response.model}")
print(f"tokens        : {usage.prompt_tokens} in + {usage.completion_tokens} out = {usage.total_tokens}")

# %% [markdown]
# ## Streaming
#
# Same request, `stream=True`: you get deltas instead of one blob. Nothing about
# the model changes - this is purely how the HTTP response is framed.
#
# `stream_options={"include_usage": True}` is not optional politeness either:
# without it a streamed response carries **no token counts at all**, so anything
# counting your spend - your own logging, or the workshop's APIM gateway - has to
# guess. Ask for the usage chunk; it arrives second-to-last.

# %%
stream = client.chat.completions.create(
    model=profile.model,
    messages=[{"role": "user", "content": "Name three blue things. One line."}],
    stream=True,
    stream_options={"include_usage": True},
)
for chunk in stream:
    if chunk.choices and chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
    # The spec'd usage chunk has no choices. Foundry Local 0.10 also attaches a
    # running `usage` to every content chunk - count only the final one.
    if chunk.usage and not chunk.choices:
        print(f"\n(streamed, {chunk.usage.total_tokens} tokens)")
