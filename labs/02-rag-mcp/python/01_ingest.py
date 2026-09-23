# STARTER - complete the TODO block(s). The finished version is in solution/01_ingest.py
"""Lab 2 · step 1 — ingest: PDF -> text -> chunks.

MarkItDown turns the PDFs in ../../data into markdown-ish text (saved to ../../build/*.md so you can LOOK at it),
then we cut the text into overlapping chunks and write ../../build/chunks.jsonl — a language-neutral artifact that the
C# and TypeScript versions of this lab read too.
"""
import json
from pathlib import Path

from markitdown import MarkItDown

LABS = next(p for p in Path(__file__).resolve().parents if (p / "_tools" / "make_starters.py").exists())  # labs/ root
DATA, BUILD = LABS / "02-rag-mcp" / "data", LABS / "02-rag-mcp" / "build"
CHUNK_CHARS = 700                                    # try 300 and 1500 and compare the answers in step 3


def chunk(text: str, max_chars: int = CHUNK_CHARS) -> list[str]:
    """Greedy paragraph packing with a one-paragraph overlap between neighbouring chunks."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    # TODO 1: pack paragraphs into chunks of at most max_chars; start each new chunk with the last paragraph of the previous one (overlap)
    raise NotImplementedError("TODO 1: pack paragraphs into chunks of at most max_chars; start each new chunk with the last paragraph of the previous one (overlap)")


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
