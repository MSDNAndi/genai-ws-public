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
# # 01 - Ingest: PDF to text to chunks
#
# ingest: PDF -> text -> chunks.
#
# MarkItDown turns the PDFs in ../../data into markdown-ish text (saved to ../../build/*.md so you can LOOK at it),
# then we cut the text into overlapping chunks and write ../../build/chunks.jsonl — a language-neutral artifact that the
# C# and TypeScript versions of this lab read too.
#
# *Ported from the course labs (`labs/02-rag-mcp/python/solution`) on 2026-09-23.*
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
from pathlib import Path

from markitdown import MarkItDown

LABS = Path(__file__).resolve().parents[1]   # samples/<segment>/ (was: labs/ root)
DATA, BUILD = LABS / "data", LABS / "build"
CHUNK_CHARS = 700                                    # try 300 and 1500 and compare the answers in step 3


def chunk(text: str, max_chars: int = CHUNK_CHARS) -> list[str]:
    """Greedy paragraph packing with a one-paragraph overlap between neighbouring chunks."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    # >>> TODO 1: pack paragraphs into chunks of at most max_chars; start each new chunk with the last paragraph of the previous one (overlap)
    chunks, current = [], []
    for para in paragraphs:
        if current and sum(len(p) + 2 for p in current) + len(para) > max_chars:
            chunks.append("\n\n".join(current))
            current = [current[-1]]                  # overlap: keep context across the boundary
        current.append(para)
    if current:
        chunks.append("\n\n".join(current))
    return chunks
    # <<< TODO


BUILD.mkdir(exist_ok=True)
md = MarkItDown()
records = []
for pdf in sorted(DATA.glob("*.pdf")):
    text = md.convert(str(pdf)).text_content
    (BUILD / f"{pdf.stem}.md").write_text(text, encoding="utf-8")
    pieces = chunk(text)
    for i, piece in enumerate(pieces):
        records.append({"id": f"{pdf.stem}#{i}", "doc": pdf.name, "chunk": i, "text": piece})
    print(f"{pdf.name}: {len(text):>5} chars -> {len(pieces)} chunks")

with open(BUILD / "chunks.jsonl", "w", encoding="utf-8") as fh:
    for r in records:
        fh.write(json.dumps(r, ensure_ascii=False) + "\n")
print(f"\n{len(records)} chunks -> {BUILD / 'chunks.jsonl'}")
print("Now open build/kestrel_operations_handbook.md and look at what happened to the fleet TABLE. (PDFs lie.)")
