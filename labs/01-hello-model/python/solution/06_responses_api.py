"""Lab 1 · stretch — the Responses API: the newer dialect at OpenAI and Foundry (/openai/v1/responses).

Differences to Chat Completions you can see here: `input` + `instructions` instead of messages; server-side
conversation state via `previous_response_id`; typed output items; streaming as semantic events.
Works on Foundry and OpenAI. Local runners and gateways may only speak Chat Completions — that is why every
other lab uses Chat Completions (see research/2026-09-22_framework-snippet-verification.md).
"""
import os

from dotenv import find_dotenv, load_dotenv
from pathlib import Path as _Path
from openai import OpenAI

_here = _Path(globals().get("__file__", ".")).resolve()   # no __file__ in a notebook: start at the cwd
for _folder in [*_here.parents, _Path.cwd(), *_Path.cwd().parents]:
    if (_folder / ".env").is_file():   # every .env from this file upward: the nearest one wins,
        load_dotenv(_folder / ".env")  # so labs/.env or one .env at the repo root both work
BASE, KEY, MODEL = os.environ["GENAI_BASE_URL"], os.environ["GENAI_API_KEY"], os.environ["GENAI_MODEL"]
HEADERS = {"api-key": KEY} if os.getenv("GENAI_KEY_HEADER", "api-key") == "api-key" else None
client = OpenAI(base_url=BASE, api_key=KEY, default_headers=HEADERS)
# The Responses API spells the reasoning knob differently: reasoning={"effort": ...}
EXTRA = {"reasoning": {"effort": os.environ["GENAI_REASONING_EFFORT"]}} if os.getenv("GENAI_REASONING_EFFORT") else {}

first = client.responses.create(model=MODEL, instructions="Be brief.", **EXTRA,
                                input="Name one advantage of running a model locally.")
print("1:", first.output_text)

# The service keeps the conversation: refer to the previous turn by id instead of resending the history.
# (Needs the endpoint to store responses; if yours does not, resend the history as input items instead.)
try:
    second = client.responses.create(model=MODEL, previous_response_id=first.id, **EXTRA,
                                     input="And one disadvantage? Same length.")
    print("2:", second.output_text)
except Exception as e:
    print("2: previous_response_id not supported here ->", str(e)[:120])

print("3 (streamed): ", end="", flush=True)
with client.responses.stream(model=MODEL, input="Count from 1 to 5, comma separated.", **EXTRA) as stream:
    for event in stream:
        if event.type == "response.output_text.delta":
            print(event.delta, end="", flush=True)
print()
