"""Lab 2 · stretch — fix the K-4 answer: when ingestion lies, fix the ingestion.

Step 3 probably said 2.5 kg for "rain": the PDF-to-text step flattened the fleet table, so the model saw numbers
without their columns. Retrieval was fine. Fix: read tables cell by cell (pdfplumber) and add every row as a
self-contained sentence chunk ("K-4: <column> = <value>; ..."). Then run 02_embed.py, 03_ask.py and
06_eval.py again and compare. (Docling or Azure Content Understanding do this structure-aware extraction for you.)
"""
import json
from pathlib import Path

import pdfplumber

LABS = next(p for p in Path(__file__).resolve().parents if (p / "_tools" / "make_starters.py").exists())   # labs/ root
DATA, BUILD = LABS / "02-rag-mcp" / "data", LABS / "02-rag-mcp" / "build"
chunks_file = BUILD / "chunks.jsonl"                 # written by 01_ingest.py; we append to it
existing = {json.loads(line)["id"] for line in open(chunks_file, encoding="utf-8")}   # so a re-run adds nothing twice

added = []
for pdf in sorted(DATA.glob("*.pdf")):
    with pdfplumber.open(pdf) as doc:
        for page_no, page in enumerate(doc.pages, 1):
            for t, table in enumerate(page.extract_tables()):   # each table = list of rows, each row = list of cells
                header, *rows = table                           # first row holds the column names
                for r, row in enumerate(rows):
                    # >>> TODO 1: turn one table row into a sentence that keeps every value next to its column name
                    sentence = f"{row[0]}: " + "; ".join(f"{h} = {v}" for h, v in zip(header[1:], row[1:]))
                    # <<< TODO
                    cid = f"{pdf.stem}#p{page_no}t{t}r{r}"      # chunk id: page, table, row
                    if cid not in existing:
                        added.append({"id": cid, "doc": pdf.name, "chunk": cid.split("#")[1],
                                      "text": f"Table row from {pdf.stem.replace('_', ' ')}: {sentence}"})

with open(chunks_file, "a", encoding="utf-8") as fh:  # "a" = append to the existing chunks
    for rec in added:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
for rec in added:
    print("+", rec["text"])
print(f"\n{len(added)} table-row chunks added -> now run 02_embed.py, then 03_ask.py / 06_eval.py again")
