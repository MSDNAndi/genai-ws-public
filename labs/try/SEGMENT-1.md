# Segment 1 — try the live demos yourself

Each block runs in your Codespace terminal **from `labs/`** (`cd /workspaces/genai-ws-public/labs` if you are elsewhere).
Your key comes from the Codespace secret or `labs/.env`, exactly like the labs. Nothing here changes any file.

## S1 · Demo: tokens and attention, live (slide 20)

Try it:

```bash
python try/s1_tokens.py
python try/s1_tokens.py "Donaudampfschifffahrt ist schön 🚢"
```

Then open the two browser tools (any browser works, your Codespace's too):
<https://tiktokenizer.vercel.app> (pick `o200k_base`) and <https://poloclub.github.io/transformer-explainer>
(type "the cat sat on the", click one attention head, drag the temperature slider).

What to notice:
- `" strawberry"` is a single token, not ten letters — that is why letter counting trips models up.
- The German compound costs more tokens than the English sentence; an emoji can be several tokens (shown as `<raw bytes>`).
- The script and tiktokenizer give the same ids for `o200k_base`: tokenizing is plain code, not magic.

## S1 · Demo: what reasoning_effort costs — and who refuses it (slide 51)

Try it:

```bash
GENAI_MODEL=gpt-5-nano python try/s1_effort_cost.py
GENAI_MODEL=DeepSeek-V4.1-Flash-1017 python try/s1_effort_cost.py
```

What to notice:
- gpt-5-nano refuses `temperature=0.2` with a 400: reasoning models lock sampling knobs and offer `reasoning_effort` instead.
- low → medium → high: same answer, but hidden reasoning tokens grow (test run: 0 → 192 → 384) and so does the estimated bill; hidden tokens are billed as output.
- DeepSeek accepts temperature; the workshop gateway drops `reasoning_effort` for models that would reject it (DeepSeek, grok, Llama, gpt-4o-mini), so hidden stays 0. To *see* a refusal, use gpt-5-nano with temperature as above.

The longer lab version (temperature, top_p, seed, then minimal/low/high): `GENAI_MODEL=gpt-5-nano python 01-hello-model/python/solution/02_knobs.py`

Instructor-only part: the APIM response headers with tokens consumed/remaining per key (llm-token-limit policy) — the gateway side of the bill.

## S1 · Demo: one script, five providers (slide 61)

Try it:

```bash
python try/s1_five_providers.py
```

What to notice:
- One client, one URL, one key — five vendors (OpenAI, DeepSeek, xAI, Meta, OpenAI open-weight); only the model name changes.
- Compare seconds and tokens: the "fast-non-reasoning" and Flash models answer in under a second; gpt-5-nano spends extra (hidden) tokens.
- Same question, different style and length. Pick your own list: `python try/s1_five_providers.py gpt-5-nano gpt-oss-120b`.

With tool calling too (workshop model + `GENAI_MODEL_2`): `python 01-hello-model/python/solution/05_same_code_other_model.py`

Instructor-only part: the local Ollama target (gemma4:e4b, no key, no network) — a Codespace has no Ollama; run it on your own laptop.
