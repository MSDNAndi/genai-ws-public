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
# # 06 - Tables: fix the K-4 answer
#
# Lab 2 · stretch — fix the K-4 answer. Step 3 probably said 2.5 kg for "rain": the PDF-to-text step flattened the
#
# fleet table, so the model saw numbers without their columns. Retrieval was fine - ingestion lied.
#
# Fix: read tables cell by cell (pdfplumber) and add every row as a self-contained sentence chunk.
# Then run 02_embed.py, 03_ask.py and 06_eval.py again and compare. (Docling or Azure Content Understanding do this
# kind of structure-aware extraction for you.)
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

import pdfplumber

LABS = Path(__file__).resolve().parents[1]   # samples/<segment>/ (was: labs/ root)
DATA, BUILD = LABS / "data", LABS / "build"
chunks_file = BUILD / "chunks.jsonl"
existing = {json.loads(line)["id"] for line in open(chunks_file, encoding="utf-8")}

added = []
for pdf in sorted(DATA.glob("*.pdf")):
    with pdfplumber.open(pdf) as doc:
        for page_no, page in enumerate(doc.pages, 1):
            for t, table in enumerate(page.extract_tables()):
                header, *rows = table
                for r, row in enumerate(rows):
                    # >>> TODO 1: turn one table row into a sentence that keeps every value next to its column name
                    sentence = f"{row[0]}: " + "; ".join(f"{h} = {v}" for h, v in zip(header[1:], row[1:]))
                    # <<< TODO
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
