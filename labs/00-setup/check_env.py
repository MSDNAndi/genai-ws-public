"""check_env.py — is my laptop ready for the workshop?  python 00-setup/check_env.py   (from the labs folder)

Checks, in order: Python version and packages · labs/.env · the workshop endpoint (chat, tool call, structured output,
embeddings) · Ollama (optional). Every failure prints the most likely fix. Nothing here costs more than a few tokens.
"""
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):   # a redirected Windows console is cp1252 and dies on the first check mark
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
import importlib.metadata as md
import json
import os
import sys
import time
from pathlib import Path

LABS = next(p for p in Path(__file__).resolve().parents if (p / "_tools" / "make_starters.py").exists())
results = []


def report(status: str, what: str, detail: str = "") -> None:
    results.append(status)
    icon = {"ok": "✅", "warn": "⚠️ ", "fail": "❌"}[status]
    print(f"{icon} {what}" + (f"\n     {detail}" if detail else ""))


def hint(exc: Exception) -> str:
    text = str(exc)
    code = getattr(exc, "status_code", None)
    if code == 401 or "401" in text:
        return "401: key missing or wrong. Check GENAI_API_KEY and GENAI_KEY_HEADER=api-key (gateway/Foundry keys)."
    if code == 404 or "DeploymentNotFound" in text or "404" in text:
        return "404: model/deployment name or URL wrong. GENAI_BASE_URL must end with /openai/v1 (or /v1 for local)."
    if code == 429 or "429" in text:
        return "429: your per-minute token limit was hit - wait a minute, then retry."
    if code == 403 or "403" in text:
        return "403: today's token quota for your key is used up (or the key may not use this model) - ask the instructor."
    if "Connect" in type(exc).__name__ or "connect" in text.lower():
        return "Cannot connect: check the URL, Wi-Fi, VPN/proxy (HTTPS_PROXY) or that the local server runs."
    return text[:200]


# --- 1. Python and packages ------------------------------------------------------------------------------------------
v = sys.version_info
report("ok" if v >= (3, 11) else "fail", f"Python {v.major}.{v.minor}.{v.micro}",
       "" if v >= (3, 11) else "Python 3.11+ required (3.12 recommended).")
PINS = {"openai": "3.18.0", "agent-framework-core": "1.19.0", "agent-framework-openai": "1.14.4",
        "agent-framework-orchestrations": "1.2.0", "mcp": "1.30.0", "langchain": "1.4.2", "langgraph": "1.2.12",
        "markitdown": "0.1.8", "python-dotenv": "1.2.3"}
missing, drift = [], []
for pkg, want in PINS.items():
    try:
        have = md.version(pkg)
        if have != want:
            drift.append(f"{pkg} {have} (tested {want})")
    except md.PackageNotFoundError:
        missing.append(pkg)
if missing:
    report("fail", "Python packages missing: " + ", ".join(missing), "pip install -r requirements.txt  (inside your venv)")
elif drift:
    report("warn", "Python packages differ from the tested versions", "; ".join(drift))
else:
    report("ok", "Python packages match requirements.txt")
if (md.version("mcp").split(".")[0] if "mcp" not in missing else "1") != "1":
    report("fail", "mcp 2.x installed", "Agent Framework 1.19 needs mcp 1.x in the same environment: pip install mcp==1.30.0")

# --- 2. labs/.env ----------------------------------------------------------------------------------------------------
from dotenv import load_dotenv  # noqa: E402

# labs/.env, or one .env at the repo root: every .env from labs/ upward, the nearest wins
env_files = [folder / ".env" for folder in [LABS, *LABS.parents] if (folder / ".env").is_file()]
for env_file in env_files:
    load_dotenv(env_file)
if env_files:
    report("ok", "settings from " + ", ".join(str(f) for f in env_files))
else:
    report("warn", "no .env found", "copy labs/.env.example to labs/.env and fill in your handout card values")
need = ["GENAI_BASE_URL", "GENAI_API_KEY", "GENAI_MODEL", "GENAI_EMBED_MODEL"]
absent = [n for n in need if not os.getenv(n) or "<" in os.getenv(n, "")]
if absent:
    report("fail", "settings missing: " + ", ".join(absent), "edit labs/.env")
    sys.exit(1)
key = os.environ["GENAI_API_KEY"]
report("ok", f"endpoint {os.environ['GENAI_BASE_URL']} · model {os.environ['GENAI_MODEL']} · key …{key[-4:]}")

# --- 3. the workshop endpoint ----------------------------------------------------------------------------------------
from openai import OpenAI  # noqa: E402
from pydantic import BaseModel  # noqa: E402

headers = {"api-key": key} if os.getenv("GENAI_KEY_HEADER", "api-key") == "api-key" else None
client = OpenAI(base_url=os.environ["GENAI_BASE_URL"], api_key=key, default_headers=headers, timeout=120, max_retries=1)
extra = {"reasoning_effort": os.environ["GENAI_REASONING_EFFORT"]} if os.getenv("GENAI_REASONING_EFFORT") else {}
model = os.environ["GENAI_MODEL"]

try:
    t0 = time.perf_counter()
    r = client.chat.completions.create(model=model, **extra, messages=[{"role": "user", "content": "Reply with the word ready."}])
    report("ok", f"chat: '{(r.choices[0].message.content or '').strip()[:40]}' in {time.perf_counter() - t0:.1f}s")
except Exception as e:  # the first call decides whether the rest makes sense
    report("fail", "chat call failed", hint(e))
    if "reasoning_effort" in str(e):
        print("     This model rejects reasoning_effort - remove GENAI_REASONING_EFFORT from labs/.env")
    sys.exit(1)

try:
    tool = {"type": "function", "function": {"name": "get_weather", "description": "Weather for a city",
            "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}}}
    r = client.chat.completions.create(model=model, tools=[tool], **extra,
                                       messages=[{"role": "user", "content": "What's the weather in Paris?"}])
    calls = r.choices[0].message.tool_calls or []
    report("ok" if calls else "warn", "tool calling: " + (f"{calls[0].function.name}({calls[0].function.arguments})" if calls
           else "the model answered without calling the tool (try another model for Lab 1 step 4 / Lab 3)"))
except Exception as e:
    report("fail", "tool calling failed", hint(e))


class Check(BaseModel):
    ready: bool
    city: str


try:
    parsed = client.chat.completions.parse(model=model, response_format=Check, **extra, messages=[
        {"role": "user", "content": "Return ready=true and city=Mannheim."}]).choices[0].message.parsed
    report("ok" if parsed else "warn", f"structured output: {parsed.model_dump() if parsed else 'refused'}")
except Exception as e:
    report("warn", "structured output not supported by this endpoint/model", hint(e))

try:
    emb = client.embeddings.create(model=os.environ["GENAI_EMBED_MODEL"], input=["hello"], encoding_format="float")
    report("ok", f"embeddings: {os.environ['GENAI_EMBED_MODEL']} -> {len(emb.data[0].embedding)} dims")
except Exception as e:
    report("fail", "embeddings failed (needed for Lab 2)", hint(e))

# --- 4. local runtime (optional) -------------------------------------------------------------------------------------
if os.getenv("OLLAMA_BASE_URL"):
    local = OpenAI(base_url=os.environ["OLLAMA_BASE_URL"], api_key="ollama", timeout=10, max_retries=0)
    try:
        names = [m.id for m in local.models.list().data]
        wanted = [os.getenv("OLLAMA_MODEL", ""), os.getenv("OLLAMA_EMBED_MODEL", "")]
        lacking = [w for w in wanted if w and not any(n == w or n == f"{w}:latest" for n in names)]
        report("warn" if lacking else "ok", f"Ollama: {len(names)} model(s)" + (f", missing {lacking}" if lacking else ""),
               "ollama pull " + " && ollama pull ".join(lacking) if lacking else "")
    except Exception as e:
        report("warn", "Ollama not reachable (needed for Lab 1 step 5 and Lab 4)", hint(e) + "  Install from ollama.com.")

print("\n" + ("All set - see you at the workshop!" if "fail" not in results else "Please fix the ❌ items (details above)."))
print(json.dumps({"ok": results.count("ok"), "warn": results.count("warn"), "fail": results.count("fail")}))
sys.exit(1 if "fail" in results else 0)
