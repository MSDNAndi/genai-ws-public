# STARTER - complete the TODO block(s). The finished version is in solution/04_tool_loop.py
"""Lab 1 · step 4 — the tool-call loop, by hand. This loop is the foundation of every agent you will see today.

What this shows: the model cannot run code — it can only ASK for a tool. The loop is:
model -> "please call get_weather(city='Paris')" -> YOUR code runs it -> result goes back as a "tool" message ->
model answers (or asks for another tool). Frameworks (Agent Framework, LangChain, ...) run exactly this loop for you.
"""
import json
import os

from dotenv import find_dotenv, load_dotenv
from pathlib import Path as _Path
from openai import OpenAI

# ---- 1. Settings and client (same as step 1) ----
_here = _Path(globals().get("__file__", ".")).resolve()   # no __file__ in a notebook: start at the cwd
for _folder in [*_here.parents, _Path.cwd(), *_Path.cwd().parents]:
    if (_folder / ".env").is_file():   # every .env from this file upward: the nearest one wins,
        load_dotenv(_folder / ".env")  # so labs/.env or one .env at the repo root both work
BASE, KEY, MODEL = os.environ["GENAI_BASE_URL"], os.environ["GENAI_API_KEY"], os.environ["GENAI_MODEL"]
HEADERS = {"api-key": KEY} if os.getenv("GENAI_KEY_HEADER", "api-key") == "api-key" else None
client = OpenAI(base_url=BASE, api_key=KEY, default_headers=HEADERS)
# Optional "think less" knob (GENAI_REASONING_EFFORT=low); only sent when set (see step 1).
EXTRA = {"reasoning_effort": os.environ["GENAI_REASONING_EFFORT"]} if os.getenv("GENAI_REASONING_EFFORT") else {}

# ---- 2. The tools: plain Python functions (fake data, so the result is predictable) ----
FAKE_WEATHER = {"paris": (19, "light rain"), "mannheim": (22, "sunny"), "jacksonville": (31, "thunderstorms")}


def get_weather(city: str) -> str:
    temp, sky = FAKE_WEATHER.get(city.lower(), (20, "unknown"))
    return json.dumps({"city": city, "temp_c": temp, "sky": sky})    # tools return text; JSON is easy for models


def to_fahrenheit(celsius: float) -> str:
    return json.dumps({"celsius": celsius, "fahrenheit": round(celsius * 9 / 5 + 32, 1)})


# What the model SEES of each tool: a name, a description and a JSON Schema for the arguments (not the code).
TOOLS = [
    {"type": "function", "function": {
        "name": "get_weather", "description": "Current weather for a city.",
        "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}}},
    {"type": "function", "function": {
        "name": "to_fahrenheit", "description": "Convert a temperature from Celsius to Fahrenheit.",
        "parameters": {"type": "object", "properties": {"celsius": {"type": "number"}}, "required": ["celsius"]}}},
]
IMPLEMENTATIONS = {"get_weather": get_weather, "to_fahrenheit": to_fahrenheit}   # tool name -> our function

# ---- 3. The conversation so far: the model has no memory, so we resend this list every time ----
messages = [{"role": "system", "content": "Use the tools for facts. Be brief."},
            {"role": "user", "content": "What's the weather in Paris, and what is that temperature in Fahrenheit?"}]

# ---- 4. The loop: call the model, run what it asks for, send the results back, repeat ----
for step in range(6):                                   # a budget: agents need a stop condition
    response = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOLS, **EXTRA)
    msg = response.choices[0].message
    # TODO 2: append the assistant message; if it has no tool_calls print the answer and stop; otherwise run each tool and append a {'role': 'tool', ...} message per call
    raise NotImplementedError("TODO 2: append the assistant message; if it has no tool_calls print the answer and stop; otherwise run each tool and append a {'role': 'tool', ...} message per call")
else:                                                   # for-else: runs only if the loop never hit "break"
    print("Stopped: step budget exhausted.")

# Try this:
#  * Ask something that needs no tool ("Tell me a joke") — the model answers directly.
#  * Ask for three cities at once — many models return several tool_calls in ONE turn (parallel tool calls).
#  * Remove the system prompt or a tool description and watch the tool choice get worse.
