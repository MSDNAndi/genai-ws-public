# STARTER - complete the TODO block(s). The finished version is in solution/07_tables.py
"""Lab 2 · stretch — fix the K-4 answer. Step 3 probably said 2.5 kg for "rain": the PDF-to-text step flattened the
fleet table, so the model saw numbers without their columns. Retrieval was fine - ingestion lied.

Fix: read tables cell by cell (pdfplumber) and add every row as a self-contained sentence chunk.
Then run 02_embed.py, 03_ask.py and 06_eval.py again and compare. (Docling or Azure Content Understanding do this
kind of structure-aware extraction for you.)"""
import json
from pathlib import Path

import pdfplumber

LABS = next(p for p in Path(__file__).resolve().parents if (p / "_tools" / "make_starters.py").exists())
DATA, BUILD = LABS / "02-rag-mcp" / "data", LABS / "02-rag-mcp" / "build"
chunks_file = BUILD / "chunks.jsonl"
existing = {json.loads(line)["id"] for line in open(chunks_file, encoding="utf-8")}

added = []
for pdf in sorted(DATA.glob("*.pdf")):
    with pdfplumber.open(pdf) as doc:
        for page_no, page in enumerate(doc.pages, 1):
            for t, table in enumerate(page.extract_tables()):
                header, *rows = table
                for r, row in enumerate(rows):
                    # TODO 1: turn one table row into a sentence that keeps every value next to its column name
                    raise NotImplementedError("TODO 1: turn one table row into a sentence that keeps every value next to its column name")
                    cid = f"{pdf.stem}#p{page_no}t{t}r{r}"
                    if cid not in existing:
                        added.append({"id": cid, "doc": pdf.name, "chunk": cid.split("#")[1],
                                      "text": f"Table row from {pdf.stem.replace('_', ' ')}: {sentence}"})

with open(chunks_file, "a", encoding="utf-8") as fh:
    for rec in added:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
for rec in added:
    print("+", rec["text"])
print(f"\n{len(added)} table-row chunks added -> now run 02_embed.py, then 03_ask.py / 06_eval.py again")
