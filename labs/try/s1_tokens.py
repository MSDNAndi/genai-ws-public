"""Try it · Segment 1, slide 20 — tokens, counted on your own machine.

What this shows: the text a model reads is cut into tokens, and the same idea costs a different
number of tokens in English, German, code or emoji. o200k_base is the encoding of the gpt-4o / gpt-5 family.
No key, no network call to a model (tiktoken only downloads the encoding file once, ~3 MB).
Run (from labs/):  python try/s1_tokens.py            or with your own text:  python try/s1_tokens.py "Hallo Welt"
"""
import sys

try:
    import tiktoken                     # comes with the lab install (pulled in by langchain-openai)
except ImportError:
    sys.exit("tiktoken is missing -> pip install tiktoken   (then run this script again)")

enc = tiktoken.get_encoding("o200k_base")


def piece(token_id: int) -> str:
    """The text of one token. Half an emoji is not valid text on its own, so show its raw bytes instead."""
    raw = enc.decode_single_token_bytes(token_id)
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return "<" + raw.hex(" ") + ">"

# ---- 1. One sentence, token by token: the piece of text and its id ----
sentence = " ".join(sys.argv[1:]) or "How many r's are in strawberry?"
ids = enc.encode(sentence)
print(f"{sentence!r} -> {len(ids)} tokens, {len(sentence)} characters")
for i in ids:
    print(f"  {i:>7}  {piece(i)!r}")

# ---- 2. Same meaning, different languages and formats: how many tokens each? ----
samples = {
    "English": "The Danube steamship company is looking for captains.",
    "German": "Die Donaudampfschifffahrtsgesellschaft sucht Kapitäne.",
    "Code": "def is_prime(n): return n > 1 and all(n % d for d in range(2, int(n**0.5) + 1))",
    "Emoji": "🚢🌊👨‍✈️ hiring now! 🎉🎉🎉",
}
print("\nSame budget, different languages:")
for label, text in samples.items():
    toks = enc.encode(text)
    pieces = [piece(t) for t in toks]
    print(f"  {label:<8} {len(toks):>3} tokens / {len(text):>3} chars  {pieces[:12]}{' ...' if len(pieces) > 12 else ''}")

# What to notice:
#  * " strawberry" is ONE token here, not 10 letters — that is why "count the r's" is hard for a model.
#  * The German compound word breaks into many pieces: non-English text often costs more tokens (= more money, less context).
#  * One emoji can be several tokens (shown as <raw bytes>); the pilot emoji is even glued from several characters.
