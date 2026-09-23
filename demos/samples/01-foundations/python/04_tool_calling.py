# /// script
# requires-python = ">=3.12"
# dependencies = ["genaiclass", "httpx"]
#
# [tool.uv.sources]
# genaiclass = { path = "../../../shared/python", editable = true }
# ///
# %% [markdown]
# # 04 - The tool-calling loop
#
# This is the single most important sample in the workshop. Every agent
# framework you will meet today - Microsoft Agent Framework, LangGraph,
# PydanticAI, the OpenAI and Claude Agent SDKs - is this `while` loop with
# better ergonomics around it.
#
# The model never runs anything. It emits *a request to run something*, you run
# it, you hand the result back, and it continues. Write the loop once by hand and
# no framework will ever be a black box again.
#
# ```bash
# uv run 04_tool_calling.py --profile mock
# ```

# %%
import json
import os

import httpx

from genaiclass import banner, get_profile, make_client

profile = get_profile()
client = make_client(profile)
print(banner(profile))

# %% [markdown]
# ## 1. The functions - ordinary Python, no AI involved
#
# `get_route` calls openrouteservice.org when `OPENROUTESERVICE_API_KEY` is set
# and otherwise returns a plausible stub, so the loop is demonstrable offline.

# %%
ORS_KEY = os.environ.get("OPENROUTESERVICE_API_KEY", "")


def get_route(origin: str, destination: str) -> dict:
    """Distance and duration for driving from origin to destination."""
    if not ORS_KEY:
        return {"origin": origin, "destination": destination, "distance_km": 42.0,
                "duration_min": 35.0, "source": "stub (no ORS key set)"}

    def geocode(place: str) -> list[float]:
        response = httpx.get("https://api.openrouteservice.org/geocode/search",
                             params={"api_key": ORS_KEY, "text": place, "size": 1}, timeout=20)
        response.raise_for_status()
        return response.json()["features"][0]["geometry"]["coordinates"]

    body = {"coordinates": [geocode(origin), geocode(destination)]}
    response = httpx.post("https://api.openrouteservice.org/v2/directions/driving-car",
                          headers={"Authorization": ORS_KEY}, json=body, timeout=30)
    response.raise_for_status()
    summary = response.json()["routes"][0]["summary"]
    return {"origin": origin, "destination": destination,
            "distance_km": round(summary["distance"] / 1000, 1),
            "duration_min": round(summary["duration"] / 60),
            "source": "openrouteservice.org"}


def get_current_weather(location: str) -> dict:
    """Deliberately fake - it is here to prove the model picks between tools."""
    return {"location": location, "temperature_c": 18, "conditions": "light rain"}


TOOL_IMPLEMENTATIONS = {"get_route": get_route, "get_current_weather": get_current_weather}

# %% [markdown]
# ## 2. The descriptions - this is the prompt engineering that matters
#
# The model sees nothing but these names, descriptions and schemas. A vague
# description is a bug: it is how the model decides *whether* to call you and
# *what* to put in the arguments.

# %%
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_route",
            "description": "Driving distance and duration between two places. "
                           "Use for any question about how far or how long a drive is.",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin": {"type": "string", "description": "Start, e.g. Bellevue, WA"},
                    "destination": {"type": "string", "description": "End, e.g. Redmond, WA"},
                },
                "required": ["origin", "destination"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "Current weather conditions for one place.",
            "parameters": {
                "type": "object",
                "properties": {"location": {"type": "string"}},
                "required": ["location"],
                "additionalProperties": False,
            },
        },
    },
]

# %% [markdown]
# ## 3. The loop
#
# 1. send the conversation plus the tool catalogue
# 2. if `finish_reason == "tool_calls"`, run every requested call
# 3. append the assistant turn **and** one `tool` message per call - the ids must
#    match, or the next request is rejected
# 4. go back to 1; stop when the model answers in prose
#
# `max_turns` is not optional politeness. Without it, a confused model and a
# failing tool will bill you in a tight loop.

# %%
def run_conversation(question: str, max_turns: int = 6) -> str:
    messages: list[dict] = [
        {"role": "system",
         "content": "You are a travel assistant. Use the tools; never guess numbers."},
        {"role": "user", "content": question},
    ]

    for turn in range(1, max_turns + 1):
        response = client.chat.completions.create(
            model=profile.model, messages=messages, tools=TOOLS,
        )
        message = response.choices[0].message
        messages.append(message.model_dump(exclude_none=True))

        if not message.tool_calls:
            print(f"  turn {turn}: answered")
            return message.content or ""

        for call in message.tool_calls:
            name = call.function.name
            arguments = json.loads(call.function.arguments or "{}")
            print(f"  turn {turn}: model wants {name}({arguments})")
            try:
                result = TOOL_IMPLEMENTATIONS[name](**arguments)
            except Exception as error:  # hand failures back as data, never crash the loop
                result = {"error": f"{type(error).__name__}: {error}"}
            messages.append({"role": "tool", "tool_call_id": call.id,
                             "content": json.dumps(result)})

    return "(gave up - hit max_turns)"


print(run_conversation(
    "How far is it from Bellevue, WA to Redmond, WA, and what is the weather there?"))

# %% [markdown]
# ## What you just built
#
# * **Parallel tool calls** - `message.tool_calls` is a list; good models ask for
#   route and weather in one turn. Handle all of them before replying.
# * **Errors are data.** Returning an error object lets the model apologise or
#   retry; raising kills the run.
# * **The catalogue is context.** Every tool costs tokens on every single turn.
#   Twenty tools is a design smell - that is what MCP servers and sub-agents fix.
# * **Nothing here is provider-specific.** Swap `--profile` and the same loop
#   runs against a local model, as long as it was trained for tool calls.
