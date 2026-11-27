"""Read the printed folio of every table-of-contents entry out of a real render.

    ml/bin/python toc_pages.py /tmp/pass1.docx      ->  artifacts/toc_pages.json

The table of contents is written by build_project.py from artifacts/toc_pages.json, and
that file cannot be known before the document exists. This closes the loop: build once
with blank folios, render that build, read the folios back, build again.

Why the numbers are baked in rather than left to a Word field: the document is read in
viewers (Google Docs, Word for the web, print shops) that never recalculate fields, and a
field with no cached result prints as nothing. Each number is therefore written as the
cached result of a PAGEREF field, so it is visible everywhere and still refreshable in
Word.

How each entry is located:

* front matter is found by its heading text, searched only within the pages before the
  body starts, which is what keeps the declaration from resolving to its own line in the
  table of contents;
* chapters, references and appendices are taken from the PDF outline (LibreOffice exports
  one from the Heading styles), matched by title prefix, so a chapter heading and its
  opening section resolve to the same page;
* sections are matched to outline level 2 titles by full title equality.

Every folio is taken from the page footer that LibreOffice actually printed, and computed
from the page position only when no footer is found.
"""
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SOFFICE = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
META = os.path.join(HERE, "artifacts", "toc_meta.json")
PAGES = os.path.join(HERE, "artifacts", "toc_pages.json")

ROMAN = re.compile(r"^[ivxlcdm]+$", re.I)
DIGITS = re.compile(r"^\d+$")


def render(docx, outdir):
    """Convert the document to PDF with LibreOffice; return the PDF path."""
    subprocess.run([SOFFICE, "--headless", "--convert-to", "pdf", "--outdir", outdir, docx],
                   check=True, capture_output=True, timeout=900)
    pdf = os.path.join(outdir, os.path.splitext(os.path.basename(docx))[0] + ".pdf")
    if not os.path.exists(pdf):
        raise SystemExit("LibreOffice produced no PDF for " + docx)
    return pdf


def norm(s):
    return re.sub(r"\s+", " ", s or "").strip().upper()


def roman(n):
    table = ((1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"), (90, "xc"),
             (50, "l"), (40, "xl"), (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i"))
    out = ""
    for value, letters in table:
        while n >= value:
            out += letters
            n -= value
    return out or "i"


def outline(reader):
    """Flatten the PDF outline to [(level, title, page_index)]."""
    flat = []

    def walk(items, level):
        for it in items:
            if isinstance(it, list):
                walk(it, level + 1)
            else:
                flat.append((level, getattr(it, "title", "") or "",
                             reader.get_destination_page_number(it)))

    walk(reader.outline, 0)
    return flat


def main():
    docx = sys.argv[1] if len(sys.argv) > 1 else "/tmp/pass1.docx"
    entries = json.load(open(META, encoding="utf-8"))
    from pypdf import PdfReader

    tmp = tempfile.mkdtemp(prefix="tocrender")
    reader = PdfReader(render(docx, tmp))
    texts = [p.extract_text() or "" for p in reader.pages]
    ol = outline(reader)
    print(f"rendered {len(texts)} pages, outline {len(ol)} items from {os.path.basename(docx)}")
    if not ol:
        raise SystemExit("no PDF outline: cannot locate chapter pages")

    body_start = min(pg for lvl, _, pg in ol if lvl == 0)
    print(f"front matter: pages 1-{body_start} | body folio 1 starts at pdf page {body_start + 1}")

    def folio(idx):
        """The printed number: the footer LibreOffice drew, else computed from position."""
        lines = [l.strip() for l in texts[idx].splitlines() if l.strip()]
        for line in lines[:3]:
            if DIGITS.match(line) or ROMAN.match(line):
                return line
        if idx < body_start:
            return roman(idx + 1)
        return str(idx - body_start + 1)

    def find_page(key, start):
        """First page at or after `start` carrying the key alone on a line.

        Whole-line matching is what stops a heading from resolving to the table of
        contents line that lists it: "List of Tables" is a line of the contents, but the
        heading is the only place it stands on a line by itself.
        """
        k = norm(key)
        for i in range(start, len(texts)):
            if k in [norm(l) for l in texts[i].splitlines() if l.strip()]:
                return i
        return None

    out, misses, cursor = {}, [], 0
    for e in entries:
        label, level, search = e["label"], e["level"], e["search"]
        idx = None
        if level == 0:                                  # front matter
            if norm(label) == "TITLE PAGE":
                idx = 0
            else:
                idx = find_page(search, cursor)
        elif level == 1:                                # chapters, references, appendices
            s = norm(search)
            hits = [pg for lvl, title, pg in ol if lvl == 0 and title and s.startswith(norm(title))]
            idx = min(hits) if hits else find_page(search, cursor)
        else:                                           # sections, by exact title
            s = norm(search)
            hits = [pg for lvl, title, pg in ol if lvl == 1 and norm(title) == s]
            if not hits:
                hits = [pg for lvl, title, pg in ol if lvl >= 1 and norm(title) == s]
            idx = min(hits) if hits else find_page(search, cursor)
        if idx is None:
            misses.append((label, search))
            continue
        cursor = max(cursor, idx)
        out[label] = folio(idx)

    with open(PAGES, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    print(f"folios: {len(out)} of {len(entries)} entries -> {PAGES}")
    if misses:
        print("UNRESOLVED (left blank):")
        for label, search in misses:
            print(f"   {label}  [search: {search}]")
    for label in list(out)[:8] + list(out)[-5:]:
        print(f"   {label[:46]:48} {out[label]}")


if __name__ == "__main__":
    main()
