"""Lab 1 · step 1 — your first call.

The same 10 lines talk to Azure AI Foundry, the workshop gateway, OpenAI, Ollama, LM Studio, Foundry Local, vLLM ...
Only three things change between them: base_url, the key, and the model name.
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
# The workshop gateway (and Foundry keys) expect the key in an "api-key" header, not only as a Bearer token.
HEADERS = {"api-key": KEY} if os.getenv("GENAI_KEY_HEADER", "api-key") == "api-key" else None

client = OpenAI(base_url=BASE, api_key=KEY, default_headers=HEADERS)
# Optional: GENAI_REASONING_EFFORT=low (gpt-5 family) or none (local "thinking" models) keeps answers fast and cheap
EXTRA = {"reasoning_effort": os.environ["GENAI_REASONING_EFFORT"]} if os.getenv("GENAI_REASONING_EFFORT") else {}

response = client.chat.completions.create(
    model=MODEL,
    **EXTRA,
    messages=[
        {"role": "system", "content": "You are a concise assistant for a developer workshop."},
        {"role": "user", "content": "In two sentences: what is a token, and why should a developer care?"},
    ],
)

print(response.choices[0].message.content)
usage = response.usage
print(f"\n[{response.model}] prompt={usage.prompt_tokens} completion={usage.completion_tokens} "
      f"total={usage.total_tokens} tokens · finish_reason={response.choices[0].finish_reason}")

# Try this:
#  1. Change the system prompt ("answer like a pirate", "answer in German") and run again.
#  2. print(response.model_dump_json(indent=2))  — look at everything that came back (ids, usage, filters...).
#  3. Set GENAI_MODEL=<another deployment> in labs/.env and compare.
