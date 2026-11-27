#!/bin/bash
# rebuild the contents page in the exemplar's layout, close the folio loop, verify
set -e
cd /Users/amarachi/Downloads/Stella_Project
PY=ml/bin/python
SOFFICE=/Applications/LibreOffice.app/Contents/MacOS/soffice
FINAL=/Users/amarachi/Downloads/Stella_Project_FINAL.docx

echo "--- pass A: build, then read the folios back ---"
$PY build_project.py /tmp/q1.docx | tail -1
$PY toc_pages.py /tmp/q1.docx | head -3
cp artifacts/toc_pages.json /tmp/pages_c.json

echo "--- pass B: rebuild the deliverable ---"
$PY build_project.py "$FINAL" | tail -1
$PY toc_pages.py "$FINAL" | head -3
if diff -q /tmp/pages_c.json artifacts/toc_pages.json >/dev/null; then
  echo "FOLIOS STABLE: pass A == pass B"; else echo "FOLIOS MOVED:"; diff /tmp/pages_c.json artifacts/toc_pages.json; fi

echo "--- render ---"
$SOFFICE --headless --convert-to pdf --outdir /Users/amarachi/Downloads "$FINAL" >/dev/null 2>&1

$PY - <<'PY'
import json, re
from pypdf import PdfReader
from docx import Document

r = PdfReader("/Users/amarachi/Downloads/Stella_Project_FINAL.pdf")
print(f"pages: {len(r.pages)}")
blank = [i+1 for i,p in enumerate(r.pages) if len([l for l in (p.extract_text() or '').splitlines() if l.strip()]) <= 1]
print("blank pages:", blank or "none")

# where the contents block is and how it is laid out
def rows(i):
    out = []
    def vis(t, cm, tm, fd, fs):
        s = t.replace("\n","").strip()
        if s: out.append((round(tm[5]/28.3465,2), round(tm[4]/28.3465,2), s))
    r.pages[i].extract_text(visitor_text=vis)
    out.sort(key=lambda x: (-x[0], x[1]))
    return out

start = next(i for i,p in enumerate(r.pages) if "TABLE OF CONTENTS" in (p.extract_text() or ""))
print(f"\n=== contents layout (pdf page {start+1}, A4 {float(r.pages[start].mediabox.width)/28.3465:.2f} cm wide) ===")
rr = rows(start)
seen=set(); prev_y=None
for y,x,t in rr:
    k=(round(y,1), t[:16])
    if k in seen: continue
    seen.add(k)
    gap = "" if prev_y is None else f"gap {prev_y-y:.2f}cm"
    prev_y = y
    print(f"   y={y:6.2f} x={x:6.2f} {gap:11} {t[:50]!r}")

# every contents line must carry a folio: catches a wrapped entry
pages_txt = [r.pages[i].extract_text() or "" for i in range(len(r.pages))]
lines = [l.strip() for i in range(start, start+5) for l in pages_txt[i].splitlines() if l.strip()]
entries = [l for l in lines if re.search(r"(i|ii|iii|iv|v|vi|vii|viii|ix|x|\d+)$", l) and not l.startswith("TABLE OF")]
nolines = [l for l in lines if l and not re.search(r"\s(i|ii|iii|iv|v|vi|vii|viii|ix|x|\d+)$", l)]
print(f"\ncontents lines: {len(lines)} | entries ending in a folio: {len(entries)}")
print("lines carrying no folio (should be only the 'Page' head):", [l[:40] for l in nolines])

d = Document("/Users/amarachi/Downloads/Stella_Project_FINAL.docx")
ps = d.paragraphs
ti = next(i for i,x in enumerate(ps) if x.text.strip() == "TABLE OF CONTENTS")
tl = [x for x in ps[ti+1:ti+62] if x.text.strip()]
print(f"\nstored entries: {len(tl)} | first: {tl[0].text!r} | section form: {tl[10].text!r}")
print(f"line spacing of entries: {sorted({p.paragraph_format.line_spacing for p in tl[:12]})}")
print(f"right indent (cm): {tl[1].paragraph_format.right_indent.cm:.2f}")
PY
ls -la "$FINAL" /Users/amarachi/Downloads/Stella_Project_FINAL.pdf | awk '{print $5, $9}'
