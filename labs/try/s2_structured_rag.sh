#!/usr/bin/env bash
# Segment 2 · try it — "does the table survive?" (slide 79).
# The instructor runs Docling -> pgvector. Your version: the Lab 2 pipeline (MarkItDown + in-memory vectors), then
# structure-aware table extraction (pdfplumber, Lab 2's 07_tables.py) - same question before and after.
#   bash try/s2_structured_rag.sh        (from labs/)
set -e
cd "$(dirname "$0")/../02-rag-mcp/python/solution"
Q1="What is the maximum payload of a K-4 Kestrel in rain?"
Q2="Who is the CEO of Kestrel?"

echo "=== 1. plain text extraction (MarkItDown): the fleet table is flattened ==="
python 01_ingest.py > /dev/null           # PDFs -> build/*.md + build/chunks.jsonl
echo "--- the fleet table as plain text (build/kestrel_operations_handbook.md): which number is rain? ---"
grep -m1 -A12 "K-2 Sparrow" ../../build/kestrel_operations_handbook.md | grep -v "^$" | head -10 || true
python 02_embed.py > /dev/null            # chunks -> vectors -> build/index.json
python 03_ask.py "$Q1" "$Q2"

echo; echo "=== 2. structure-aware: every table row becomes a self-contained sentence ==="
python 07_tables.py | grep -i "K-4" || true
python 02_embed.py > /dev/null
python 03_ask.py "$Q1" "$Q2"
