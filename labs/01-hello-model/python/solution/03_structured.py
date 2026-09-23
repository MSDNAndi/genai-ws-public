"""Lab 1 · step 3 — structured output: a JSON Schema is a contract, not a hope.

We describe the shape with Pydantic; the SDK turns it into a JSON Schema, the service constrains decoding to it,
and we get a typed object back (no regex, no "please answer in JSON").
"""
import os

from dotenv import find_dotenv, load_dotenv
from pathlib import Path as _Path
from openai import OpenAI
from pydantic import BaseModel, Field

_here = _Path(globals().get("__file__", ".")).resolve()   # no __file__ in a notebook: start at the cwd
for _folder in [*_here.parents, _Path.cwd(), *_Path.cwd().parents]:
    if (_folder / ".env").is_file():   # every .env from this file upward: the nearest one wins,
        load_dotenv(_folder / ".env")  # so labs/.env or one .env at the repo root both work
BASE, KEY, MODEL = os.environ["GENAI_BASE_URL"], os.environ["GENAI_API_KEY"], os.environ["GENAI_MODEL"]
HEADERS = {"api-key": KEY} if os.getenv("GENAI_KEY_HEADER", "api-key") == "api-key" else None
client = OpenAI(base_url=BASE, api_key=KEY, default_headers=HEADERS)
# Optional: GENAI_REASONING_EFFORT=low (gpt-5 family) or none (local "thinking" models) keeps answers fast and cheap
EXTRA = {"reasoning_effort": os.environ["GENAI_REASONING_EFFORT"]} if os.getenv("GENAI_REASONING_EFFORT") else {}

TEXT = ("Tomorrow at 10:50 the second segment starts: a 40-minute talk called 'The context window is the product', "
        "covering embeddings, RAG, MCP and prompt injection, followed by a 30-minute hands-on lab.")


# >>> TODO 1: describe the shape you want back — a Session with title, start time, talk minutes, lab minutes and a list of topics
class Session(BaseModel):
    title: str
    start: str = Field(description="start time as HH:MM")
    talk_minutes: int
    lab_minutes: int
    topics: list[str]
# <<< TODO


completion = client.chat.completions.parse(
    model=MODEL,
    **EXTRA,
    messages=[{"role": "system", "content": "Extract the session described by the user."},
              {"role": "user", "content": TEXT}],
    response_format=Session,
)
session = completion.choices[0].message.parsed      # a real Session instance (or None if the model refused)
print(session.model_dump_json(indent=2) if session else completion.choices[0].message.refusal)
print("\nThe JSON Schema that was sent:", list(Session.model_json_schema()["properties"]))
print(f"Total minutes: {session.talk_minutes + session.lab_minutes}" if session else "")

# Try this: add `room: str | None` or an Enum field (level: beginner/advanced) and see what the model does with
# information that is NOT in the text.
