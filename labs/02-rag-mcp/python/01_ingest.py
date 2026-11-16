# STARTER - complete the TODO block(s). The finished version is in solution/01_ingest.py
"""Lab 2 · step 1 — ingest: PDF -> text -> chunks.

RAG (retrieval-augmented generation = look it up, then answer) starts here: the model can only use what we can find.
MarkItDown turns each PDF in data/ into markdown-ish text (saved as build/*.md so you can LOOK at it), then we cut
the text into overlapping chunks (small searchable pieces) and write build/chunks.jsonl.
Notice: the overlap, and what happens to the fleet TABLE in build/kestrel_operations_handbook.md.
C# and TypeScript skip this step and read the same chunks.jsonl format.
"""
import json
from pathlib import Path

from markitdown import MarkItDown

# --- where things live: walk up from this file to labs/ (the folder that has _tools/) ---------------------------------
LABS = next(p for p in Path(__file__).resolve().parents if (p / "_tools" / "make_starters.py").exists())  # labs/ root
DATA, BUILD = LABS / "02-rag-mcp" / "data", LABS / "02-rag-mcp" / "build"
CHUNK_CHARS = 700                                    # try 300 and 1500 and compare the answers in step 3


# --- chunking: small enough to be precise, big enough to keep a fact together ------------------------------------------
def chunk(text: str, max_chars: int = CHUNK_CHARS) -> list[str]:
    """Greedy paragraph packing with a one-paragraph overlap between neighbouring chunks."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]   # blank line = paragraph break
    # TODO 1: pack paragraphs into chunks of at most max_chars; start each new chunk with the last paragraph of the previous one (overlap)
    raise NotImplementedError("TODO 1: pack paragraphs into chunks of at most max_chars; start each new chunk with the last paragraph of the previous one (overlap)")


# --- PDF -> text -> chunks, one record per chunk --------------------------------------------------------------------
BUILD.mkdir(exist_ok=True)
md = MarkItDown()
records = []
for pdf in sorted(DATA.glob("*.pdf")):
    text = md.convert(str(pdf)).text_content
    (BUILD / f"{pdf.stem}.md").write_text(text, encoding="utf-8")   # keep the extracted text so you can inspect it
    pieces = chunk(text)
    for i, piece in enumerate(pieces):
        # the id "<doc>#<n>" is what answers will cite later
        records.append({"id": f"{pdf.stem}#{i}", "doc": pdf.name, "chunk": i, "text": piece})
    print(f"{pdf.name}: {len(text):>5} chars -> {len(pieces)} chunks")

# JSON Lines: one JSON object per line, easy to read from any language
with open(BUILD / "chunks.jsonl", "w", encoding="utf-8") as fh:
    for r in records:
        fh.write(json.dumps(r, ensure_ascii=False) + "\n")
print(f"\n{len(records)} chunks -> {BUILD / 'chunks.jsonl'}")
print("Now open build/kestrel_operations_handbook.md and look at what happened to the fleet TABLE. (PDFs lie.)")
