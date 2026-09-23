# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "genaiclass",
#     "openai==3.18.0",
#     "python-dotenv==1.2.3",
#     "numpy>=1.26",
#     "pydantic>=2.10,<3",
#     "mcp==1.30.0",
#     "markitdown[pdf]==0.1.8",
#     "pillow>=10",
# ]
#
# [tool.uv.sources]
# genaiclass = { path = "../../../shared/python", editable = true }
# ///
# %% [markdown]
# # 01 - Local models, measured
#
# your Lab 1 code, on your own machine. Same client, local base_url, and now we MEASURE:
#
# time to first token and tokens per second (streamed), plus whether the model can call a tool.
#
# Runtimes are found from labs/.env: OLLAMA_BASE_URL, LMSTUDIO_BASE_URL, FOUNDRY_LOCAL_BASE_URL (Foundry Local picks a
# port at start-up: run `foundry service status` and copy the URL + /v1).
#
# *Ported from the course labs (`labs/04-local-media/python/solution`) on 2026-09-23.*
# %%
import sys
# Windows consoles default to cp1252; one non-ASCII print (a check mark, an arrow)
# kills a demo mid-run. Switch this process's console streams to UTF-8.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, OSError):
        pass
# These samples came from the labs and read GENAI_* variables directly. --profile <name>
# (the runner always passes one) maps a providers.json profile onto those variables, so
# `--profile mock` or `p` in the runner work here exactly like in Segments 1 and 3.
if "--profile" in sys.argv:
    import os
    from genaiclass import get_profile
    _i = sys.argv.index("--profile"); _name = sys.argv[_i + 1]; del sys.argv[_i:_i + 2]
    _p = get_profile(_name)
    os.environ.update(GENAI_BASE_URL=_p.base_url, GENAI_API_KEY=_p.api_key or "none",
                      GENAI_MODEL=_p.model, GENAI_EMBED_MODEL=_p.embed_model,
                      GENAI_KEY_HEADER="api-key" if _p.key_header == "api-key" else "authorization")
    if _name == "mock":                      # the mock has no reasoning knob
        os.environ.pop("GENAI_REASONING_EFFORT", None)
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
    ("Foundry Local", "FOUNDRY_LOCAL_BASE_URL", "FOUNDRY_LOCAL_MODEL"),
    ("llama.cpp", "LLAMACPP_BASE_URL", "LLAMACPP_MODEL")] if os.getenv(var)]
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
    # One runtime misbehaving (e.g. Foundry Local with no model loaded drops the connection mid-stream)
    # must not kill the comparison - report it and move on to the next runtime.
    try:
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
    except Exception as e:
        print(f"   failed during the run: {type(e).__name__}: {str(e)[:120]}")

if not RUNTIMES:
    print("No local runtime configured - set OLLAMA_BASE_URL (and OLLAMA_MODEL) in labs/.env")
