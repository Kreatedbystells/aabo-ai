#!/bin/bash
# close the table-of-contents loop and prove the result
set -e
cd /Users/amarachi/Downloads/Stella_Project
PY=ml/bin/python
SOFFICE=/Applications/LibreOffice.app/Contents/MacOS/soffice
FINAL=/Users/amarachi/Downloads/Stella_Project_FINAL.docx

echo "--- pass A: build with current folios, re-read them ---"
$PY build_project.py /tmp/p4.docx | tail -1
$PY toc_pages.py /tmp/p4.docx | head -3
cp artifacts/toc_pages.json /tmp/pages_b.json

echo "--- pass B: rebuild the deliverable with the corrected folios ---"
$PY build_project.py "$FINAL" | tail -1
$PY toc_pages.py "$FINAL" | head -3

echo "--- folios stable across the two passes? ---"
if diff -q /tmp/pages_b.json artifacts/toc_pages.json >/dev/null; then echo "IDENTICAL"; else
  echo "DIFFER:"; diff /tmp/pages_b.json artifacts/toc_pages.json; fi

echo "--- render to PDF ---"
$SOFFICE --headless --convert-to pdf --outdir /Users/amarachi/Downloads "$FINAL" >/dev/null 2>&1

$PY - <<'PY'
import json, os
from pypdf import PdfReader
from docx import Document

d = json.load(open("artifacts/toc_pages.json"))
print("=== front matter folios ===")
for k, v in list(d.items())[:10]:
    print(f"   {k:22} {v}")
print("=== last folios ===")
for k, v in list(d.items())[-4:]:
    print(f"   {k:22} {v}")

r = PdfReader("/Users/amarachi/Downloads/Stella_Project_FINAL.pdf")
print(f"=== rendered pages: {len(r.pages)} ===")
blank = []
for i, p in enumerate(r.pages):
    lines = [l.strip() for l in (p.extract_text() or "").splitlines() if l.strip()]
    if len(lines) <= 1:
        blank.append(i + 1)
print("blank pages:", blank or "none")
print("=== table of contents as printed (first 12 lines of the contents page) ===")
for l in (r.pages[6].extract_text() or "").splitlines()[:12]:
    if l.strip():
        print("   ", l.rstrip()[:88])

doc = Document("/Users/amarachi/Downloads/Stella_Project_FINAL.docx")
ps = doc.paragraphs
ti = next(i for i, x in enumerate(ps) if x.text.strip() == "TABLE OF CONTENTS")
stored = [x.text for x in ps[ti:ti + 70] if x.text.strip()]
print("=== stored .docx contents lines ===")
print("   total:", len(stored), "| front matter:", [t for t in stored[:11]])
print("   last   :", [t for t in stored[-3:]])
print("=== document totals ===")
words = sum(len(x.text.split()) for x in ps)
print(f"   paragraphs {len(ps)} | words {words} | figures {len(doc.inline_shapes)} | tables {len(doc.tables)}")
print("   GUIDE NOTEs:", sum(1 for x in ps if x.style.name == "GUIDE NOTE"))
PY
echo "--- deliverable ---"
ls -la "$FINAL" /Users/amarachi/Downloads/Stella_Project_FINAL.pdf | awk '{print $5, $9}'
