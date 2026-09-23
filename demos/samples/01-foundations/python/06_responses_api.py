# /// script
# requires-python = ">=3.12"
# dependencies = ["genaiclass"]
#
# [tool.uv.sources]
# genaiclass = { path = "../../../shared/python", editable = true }
# ///
# %% [markdown]
# # 06 - The Responses API (and what happened to Assistants)
#
# **The Assistants API was shut down on 2026-08-26.** If you have notebooks or
# code with `CreateAssistant`, `Thread`, `Run` and a polling loop in them, they
# do not run any more. This sample is the replacement.
#
# The Responses API keeps the good part of Assistants - the server remembers the
# conversation - without threads, runs or polling. One call, one object back.
#
# ```bash
# uv run 06_responses_api.py --profile mock
# ```
#
# Note: Responses is an OpenAI/Foundry-side feature. Local runners such as Ollama
# still speak Chat Completions only - which is exactly why samples 01-05 use
# Chat Completions and stay portable.

# %%
from genaiclass import banner, get_profile, make_client

profile = get_profile()
client = make_client(profile)
print(banner(profile))

# %% [markdown]
# ## One call
#
# `input` takes a plain string or the same message list you already know.
# `output_text` is the convenience accessor over a richer `output` array that can
# also hold tool calls, reasoning summaries and file citations.

# %%
response = client.responses.create(
    model=profile.model,
    instructions="You are a concise assistant. One sentence.",
    input="What is a token, in the LLM sense?",
)
print(response.output_text)
print(f"status={response.status}  id={response.id}")

# %% [markdown]
# ## State without threads
#
# This is the Assistants replacement in one parameter: `previous_response_id`
# chains a new turn onto a stored one, server-side. You stop shipping the whole
# history on every request - which is also where the prompt-caching savings come
# from.
#
# The cost: conversation state now lives on someone else's server, with their
# retention policy. `store=False` opts out and puts you back in charge of the
# history, exactly like Chat Completions.

# %%
try:
    follow_up = client.responses.create(
        model=profile.model,
        previous_response_id=response.id,
        input="Give me an example of one being split awkwardly.",
    )
    print(follow_up.output_text)
except Exception as error:
    print(f"(chained turn not supported by this endpoint: {type(error).__name__})")

# %% [markdown]
# ## Migrating the old Assistants notebooks
#
# | Assistants (dead)                      | Responses (now)                                  |
# |----------------------------------------|--------------------------------------------------|
# | `CreateAssistant(instructions, tools)` | `instructions` + `tools` on each call, or a prompt object |
# | `CreateThread` / `CreateMessage`       | `previous_response_id` (or send your own history) |
# | `CreateRun` + poll until `completed`   | the call returns the finished response            |
# | `RequiredAction` -> submit tool outputs | `function_call` items -> `function_call_output` items |
# | `code_interpreter`, `file_search`      | hosted tools with the same names                  |
# | delete assistant + thread              | nothing to clean up (or `store=False`)            |
#
# The polling loop is gone. That is roughly 60 lines of the old notebook deleted.
#
# ## Which API should you teach?
#
# * **Chat Completions** - the lingua franca. Every provider, every local runner,
#   every gateway speaks it. Use it for anything that must stay portable.
# * **Responses** - richer: hosted tools, server-side state, reasoning items,
#   built-in web/file search. Use it when you are deliberately on OpenAI or
#   Foundry and want those features.
#
# Both exist on the same endpoint. This repo defaults to Chat Completions so that
# `--profile ollama` keeps working.
