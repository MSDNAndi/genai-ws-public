"""Lab 1 · step 3 — structured output: a JSON Schema is a contract, not a hope.

What this shows: we describe the shape we want (a Pydantic class), the SDK turns it into a JSON Schema, the service
forces the model's answer to fit it, and we get a typed Python object back — no regex, no "please answer in JSON".
What to notice: you can do maths on the result (total minutes) because the fields are real ints.
"""
import os

from dotenv import find_dotenv, load_dotenv
from pathlib import Path as _Path
from openai import OpenAI
from pydantic import BaseModel, Field

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

# The free text we want to turn into data.
TEXT = ("Tomorrow at 10:50 the second segment starts: a 40-minute talk called 'The context window is the product', "
        "covering embeddings, RAG, MCP and prompt injection, followed by a 30-minute hands-on lab.")


# ---- 2. The shape we want back: field names, types and descriptions all go into the JSON Schema ----
# >>> TODO 1: describe the shape you want back — a Session with title, start time, talk minutes, lab minutes and a list of topics
class Session(BaseModel):
    title: str
    start: str = Field(description="start time as HH:MM")
    talk_minutes: int
    lab_minutes: int
    topics: list[str]
# <<< TODO


# ---- 3. The call: parse() sends the schema and turns the JSON answer into a Session ----
completion = client.chat.completions.parse(
    model=MODEL,
    **EXTRA,
    messages=[{"role": "system", "content": "Extract the session described by the user."},
              {"role": "user", "content": TEXT}],
    response_format=Session,                            # the class itself — the SDK builds the JSON Schema from it
)

# ---- 4. What came back: a real object, not a string ----
session = completion.choices[0].message.parsed      # a real Session instance (or None if the model refused)
print(session.model_dump_json(indent=2) if session else completion.choices[0].message.refusal)
print("\nThe JSON Schema that was sent:", list(Session.model_json_schema()["properties"]))
print(f"Total minutes: {session.talk_minutes + session.lab_minutes}" if session else "")   # ints, so + is maths

# Try this: add `room: str | None` or an Enum field (level: beginner/advanced) and see what the model does with
# information that is NOT in the text.
