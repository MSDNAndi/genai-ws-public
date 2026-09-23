"""Lab 4 · step 1 — your Lab 1 code, on your own machine. Same client, local base_url, and now we MEASURE:
time to first token and tokens per second (streamed), plus whether the model can call a tool.

Runtimes are found from labs/.env: OLLAMA_BASE_URL, LMSTUDIO_BASE_URL, FOUNDRY_LOCAL_BASE_URL (Foundry Local picks a
port at start-up: run `foundry service status` and copy the URL + /v1).
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
EFFORT = os.getenv("OLLAMA_REASONING_EFFORT")          # "none" = skip the thinking phase of local reasoning models
RUNTIMES = [(name, os.getenv(var), os.getenv(model_var, "")) for name, var, model_var in [
    ("Ollama", "OLLAMA_BASE_URL", "OLLAMA_MODEL"),
    ("LM Studio", "LMSTUDIO_BASE_URL", "LMSTUDIO_MODEL"),
    ("Foundry Local", "FOUNDRY_LOCAL_BASE_URL", "FOUNDRY_LOCAL_MODEL")] if os.getenv(var)]
TOOL = {"type": "function", "function": {"name": "get_weather", "description": "Current weather for a city.",
        "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}}}

for name, base, model in RUNTIMES:
    client = OpenAI(base_url=base, api_key="local", timeout=300, max_retries=0)
    try:
        available = [m.id for m in client.models.list().data]
    except Exception as e:
        print(f"\n== {name} at {base}: not reachable ({type(e).__name__})")
        continue
    model = model if model in available else (available[0] if available else model)
    print(f"\n== {name} at {base}\n   models: {', '.join(available[:8])}{' ...' if len(available) > 8 else ''}\n   using:  {model}")
    extra = {"reasoning_effort": EFFORT} if EFFORT and name == "Ollama" else {}
    t0, first, pieces = time.perf_counter(), None, 0
    stream = client.chat.completions.create(model=model, stream=True, **extra, messages=[
        {"role": "user", "content": "Write three sentences about why developers run models locally."}])
    text = ""
    for chunk in stream:
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            first = first or time.perf_counter()
            pieces += 1
            text += delta
    total = time.perf_counter() - t0
    gen = total - (first - t0) if first else 0
    print(f"   first token after {(first - t0) if first else float('nan'):.1f}s · {pieces} chunks in {gen:.1f}s "
          f"(~{pieces / gen if gen else 0:.1f} tokens/s) · {text.strip()[:100]}...")
    r = client.chat.completions.create(model=model, tools=[TOOL], **extra,
                                       messages=[{"role": "user", "content": "Weather in Heidelberg?"}])
    calls = r.choices[0].message.tool_calls or []
    print("   tool call: " + (", ".join(f"{c.function.name}({json.loads(c.function.arguments)})" for c in calls) or "none"))

if not RUNTIMES:
    print("No local runtime configured - set OLLAMA_BASE_URL (and OLLAMA_MODEL) in labs/.env")
