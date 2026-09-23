"""Lab 1 · step 5 — same code, different model. The point of the day in one script.

Runs one prompt and one tool round-trip against every endpoint it can find in labs/.env:
  the workshop endpoint (GENAI_MODEL), a second vendor behind the same key (GENAI_MODEL_2),
  local Ollama (OLLAMA_BASE_URL / OLLAMA_MODEL) and LM Studio (LMSTUDIO_BASE_URL) if they are running.
"""
import json
import os
import time

from dotenv import find_dotenv, load_dotenv
from pathlib import Path as _Path
from openai import OpenAI

_here = _Path(globals().get("__file__", ".")).resolve()   # no __file__ in a notebook: start at the cwd
for _folder in [*_here.parents, _Path.cwd(), *_Path.cwd().parents]:
    if (_folder / ".env").is_file():   # every .env from this file upward: the nearest one wins,
        load_dotenv(_folder / ".env")  # so labs/.env or one .env at the repo root both work
BASE, KEY = os.environ["GENAI_BASE_URL"], os.environ["GENAI_API_KEY"]
HEADERS = {"api-key": KEY} if os.getenv("GENAI_KEY_HEADER", "api-key") == "api-key" else None

EFFORT, LOCAL_EFFORT = os.getenv("GENAI_REASONING_EFFORT"), os.getenv("OLLAMA_REASONING_EFFORT")
targets = [("workshop endpoint", BASE, KEY, HEADERS, os.environ["GENAI_MODEL"])]
if os.getenv("GENAI_MODEL_2"):
    targets.append(("2nd vendor, same key", BASE, KEY, HEADERS, os.environ["GENAI_MODEL_2"]))
if os.getenv("OLLAMA_BASE_URL") and os.getenv("OLLAMA_MODEL"):
    targets.append(("local Ollama", os.environ["OLLAMA_BASE_URL"], "ollama", None, os.environ["OLLAMA_MODEL"]))
if os.getenv("LMSTUDIO_BASE_URL"):
    targets.append(("local LM Studio", os.environ["LMSTUDIO_BASE_URL"], "lm-studio", None, os.getenv("LMSTUDIO_MODEL", "")))

TOOL = {"type": "function", "function": {"name": "get_weather", "description": "Current weather for a city.",
        "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}}}

for label, base, key, headers, model in targets:
    client = OpenAI(base_url=base, api_key=key, default_headers=headers, timeout=180, max_retries=0)
    effort = LOCAL_EFFORT if label.startswith("local") else (EFFORT if label == "workshop endpoint" else None)
    extra = {"reasoning_effort": effort} if effort else {}
    try:
        if not model:                                   # LM Studio: take whatever model is loaded
            model = client.models.list().data[0].id
        t0 = time.perf_counter()
        r = client.chat.completions.create(model=model, **extra, messages=[
            {"role": "user", "content": "Explain retrieval-augmented generation to a developer in one sentence."}])
        chat_s = time.perf_counter() - t0
        t0 = time.perf_counter()
        r2 = client.chat.completions.create(model=model, tools=[TOOL], **extra, messages=[
            {"role": "user", "content": "What's the weather in Mannheim?"}])
        calls = r2.choices[0].message.tool_calls or []
        tool_s = time.perf_counter() - t0
        print(f"\n== {label}: {model}  ({base})")
        print(f"   chat  {chat_s:5.1f}s  {r.usage.completion_tokens if r.usage else '?'} tokens: "
              f"{(r.choices[0].message.content or '').strip()[:160]}")
        print(f"   tools {tool_s:5.1f}s  " + (", ".join(f"{c.function.name}({json.loads(c.function.arguments)})" for c in calls)
                                            or f"no tool call -> {(r2.choices[0].message.content or '')[:80]}"))
    except Exception as e:                              # a missing local runtime must not stop the comparison
        print(f"\n== {label}: {model or '?'}  skipped ({type(e).__name__}: {str(e)[:120]})")

# What to notice: identical code, different answers, latency and tool-calling habits.
# Independence = being able to make this switch in one line — and knowing what you lose or gain when you do.
