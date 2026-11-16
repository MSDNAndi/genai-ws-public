"""Try it · Segment 4, slide 170 — one model, eight clients (cloud version).

What this shows: a server answering ONE caller, then EIGHT callers at the same moment. Watch tokens per second per
request and for all requests together: a server that batches gets a much higher total while each request slows only
a little. On the instructor workstation this runs against llama.cpp and vLLM; here it runs against the workshop
gateway. Point GENAI_BASE_URL / GENAI_MODEL at your own server and the same script measures that one.
Run (from labs/):  python try/s4_eight_clients.py            or another model:  python try/s4_eight_clients.py gpt-oss-120b
"""
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# ---- 1. Settings exactly like the labs: every .env from here upward (labs/.env), real environment variables win ----
for folder in [*Path(__file__).resolve().parents, Path.cwd(), *Path.cwd().parents]:
    if (folder / ".env").is_file():
        load_dotenv(folder / ".env")
KEY = os.environ["GENAI_API_KEY"]
HEADERS = {"api-key": KEY} if os.getenv("GENAI_KEY_HEADER", "api-key") == "api-key" else None
client = OpenAI(base_url=os.environ["GENAI_BASE_URL"], api_key=KEY, default_headers=HEADERS)
MODEL = sys.argv[1] if len(sys.argv) > 1 else os.environ["GENAI_MODEL"]
EXTRA = {"reasoning_effort": os.environ["GENAI_REASONING_EFFORT"]} if os.getenv("GENAI_REASONING_EFFORT") else {}
CITIES = ["Paris", "Mannheim", "Orlando", "Tokyo", "Lagos", "Lima", "Oslo", "Perth"]


# ---- 2. One client = one small request (max 300 output tokens: 9 requests stay far below the rate limit) ----
def one_request(city: str) -> tuple[str, float, int]:
    t0 = time.perf_counter()
    r = client.chat.completions.create(model=MODEL, max_completion_tokens=300, **EXTRA, messages=[
        {"role": "user", "content": f"Describe {city} to a visitor in two short sentences."}])
    return city, time.perf_counter() - t0, r.usage.completion_tokens   # includes hidden reasoning tokens, if any


# ---- 3. n clients at once: a thread pool with n workers fires all requests at the same moment ----
def run(n: int) -> None:
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=n) as pool:
        results = list(pool.map(one_request, CITIES[:n]))
    wall = time.perf_counter() - t0
    for city, secs, tokens in results:
        print(f"  {city:<9} {secs:5.1f}s  {tokens:4d} tokens  {tokens / secs:6.1f} tok/s")
    total = sum(tokens for _, _, tokens in results)
    print(f"  => {n} client(s): {total} tokens in {wall:.1f}s wall clock = {total / wall:.1f} tok/s in total\n")


print(f"Model: {MODEL}\n1 client alone:")
run(1)
print("8 clients at the same moment:")
run(8)

# What to notice:
#  * Per-request tok/s stays roughly the same, the total is several times higher: the server serves many at once.
#  * A cloud gateway hides its hardware and adds network time; on your own GPU llama.cpp vs vLLM shows the batching gap.
