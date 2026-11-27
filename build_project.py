"""Build the NOUN project document from chapter markdown files.

Usage:  ./docxenv/bin/python build_project.py [out.docx]

Markdown conventions (deliberately small):
  # CHAPTER ONE            -> chapter heading block
  # REFERENCES             -> centred Heading 1
  ## LITERATURE REVIEW     -> centred 14pt chapter subtitle
  ### 1.1 Title            -> numbered section (Heading 2)
  #### 1.1.1 Title         -> numbered subsection (Heading 3)
  {{NOTE: text}}           -> orange guide note (delete before submission)
  {{FIG: caption}}                     -> placeholder box + numbered caption
  {{FIG: caption || PNG::/abs/path}}   -> embedded image + numbered caption
  {{TABLE: caption}}       -> table caption (auto-numbered) for the table that follows
  | a | b |                -> pipe table (first row header)
  **bold**, *italic*       -> inline runs
  - item / 1. item         -> list paragraph (hanging indent)
"""
import os, re, sys, glob

import docx
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_TAB_ALIGNMENT
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Downloads/Stella_Project_DRAFT.docx")

META = {
    "title": "AI-POWERED PHISHING DETECTION AND URL CLASSIFICATION TOOL",
    "name": "AMARACHI STELLA AWAZIE",
    "matric": "NOU241741241",
    "supervisor": "DR ADEWALE RILWAN",
    "date": "NOVEMBER, 2026",
}

# ---------------------------------------------------------------- parsing
def add_note(doc, text):
    """Add an orange guide note, stripping any enclosing {{NOTE: ...}} wrapper."""
    t = text.strip()
    if t.startswith("{{NOTE:") and t.endswith("}}"):
        t = t[7:-2].strip()
    return doc.add_paragraph(t, style="GUIDE NOTE")


def parse(path):
    blocks, buf_table = [], []
    with open(path, encoding="utf-8") as f:
        raw = f.read().split("\n")
    i = 0
    while i < len(raw):
        line = raw[i].rstrip()
        if line.startswith("|"):
            rows = []
            while i < len(raw) and raw[i].strip().startswith("|"):
                cells = [c.strip() for c in raw[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c or "-") for c in cells):
                    rows.append(cells)
                i += 1
            blocks.append(("table", rows))
            continue
        s = line.strip()
        if not s:
            i += 1
            continue
        if s.startswith("# "):
            blocks.append(("chapter", s[2:].strip()))
        elif s.startswith("## "):
            blocks.append(("subtitle", s[3:].strip()))
        elif s.startswith("### "):
            blocks.append(("section", s[4:].strip()))
        elif s.startswith("#### "):
            blocks.append(("subsection", s[5:].strip()))
        elif s.startswith("{{NOTE:") and s.endswith("}}"):
            blocks.append(("note", s[7:-2].strip()))
        elif s.startswith("{{FIG:") and s.endswith("}}"):
            blocks.append(("fig", s[6:-2].strip()))
        elif s.startswith("{{TABLE:") and s.endswith("}}"):
            blocks.append(("tablecap", s[8:-2].strip()))
        elif s.startswith("{{IMG:") and s.endswith("}}"):
            blocks.append(("img", s[6:-2].strip()))
        elif re.match(r"^[-•]\s+", s):
            blocks.append(("bullet", re.sub(r"^[-•]\s+", "", s)))
        elif re.match(r"^\d+[.)]\s+", s):
            blocks.append(("num", re.sub(r"^(\d+)[.)]\s+", r"\1.\t", s)))
        elif s.startswith("> "):
            blocks.append(("quote", s[2:].strip()))
        else:
            blocks.append(("para", s))
        i += 1
    return blocks


def fig_caption(val):
    """Caption text only: everything before an optional || PNG:: path."""
    return val.split("||")[0].strip() if "||" in val else val


def fig_path(val):
    if "||" not in val:
        return None
    tail = val.split("||", 1)[1].strip()
    return tail[5:].strip() if tail.upper().startswith("PNG::") else tail


def png_size(path):
    """Pixel dimensions from the PNG IHDR chunk (no Pillow needed)."""
    import struct
    with open(path, "rb") as fh:
        head = fh.read(26)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", head[16:24])


def collect(blocks):
    figs = [fig_caption(b[1]) for b in blocks if b[0] == "fig"]
    tabs = [b[1] for b in blocks if b[0] == "tablecap"]
    return figs, tabs


# ---------------------------------------------------------------- table of contents
# Entries are registered while the document is written, in document order. Their page
# numbers are read back from a render of that same document (toc_pages.py) and written
# in as text inside a PAGEREF field, so the number is visible in any viewer -- a field
# with no cached result shows nothing where fields are never refreshed -- while Word can
# still update it. Layout follows the department exemplar: a right-aligned "Page" column
# head, then one line per entry, tabbed to the folio, no dot leaders.
TOC_ENTRIES = []      # [{"label","level","search","bookmark","par"}]
TOC_ANCHOR = []       # the TABLE OF CONTENTS heading paragraph
TOC_STYLE = (0, 1, 2)  # front matter, chapter, section
_BM_ID = [9000]


def toc_mark(label, level, search, par):
    """Register one TOC entry and bookmark the paragraph it points at."""
    name = "_Toc%04d" % (9000 + len(TOC_ENTRIES))
    start = OxmlElement("w:bookmarkStart")
    start.set(qn("w:id"), str(_BM_ID[0])); start.set(qn("w:name"), name)
    end = OxmlElement("w:bookmarkEnd"); end.set(qn("w:id"), str(_BM_ID[0]))
    _BM_ID[0] += 1
    par._p.insert(0, start)
    par._p.append(end)
    TOC_ENTRIES.append({"label": label.strip(), "level": level,
                        "search": (search or label).strip(), "bookmark": name})


def _page_map():
    path = os.path.join(HERE, "artifacts", "toc_pages.json")
    if os.path.exists(path):
        import json
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def _folio_par(p, label, number, bold):
    """One table of contents line: the entry, a tab out to the folio column, the folio.

    The folio is written as plain text. The numbers come from a render of this same
    document (toc_pages.py), and a field would be recalculated to the page's ordinal by
    whatever application opens the file next -- which reads 1, 2, 3 where the front
    matter prints i, ii, iii. The bookmark left on the heading keeps the door open to
    turning these back into PAGEREF fields if the department ever asks for one.
    """
    m = re.match(r"^(\d+(?:\.\d+)*)\s+(.*)$", label)
    if m:                                        # a numbered section: number, tab, title
        run = p.add_run(m.group(1)); run.bold = bold
        p.add_run("\t")
        run = p.add_run(m.group(2)); run.bold = bold
    else:
        run = p.add_run(label); run.bold = bold
    p.add_run("\t")
    rn = p.add_run(str(number)); rn.bold = bold
    for r in p.runs:
        r.font.name = "Times New Roman"
        r.font.size = Pt(12)
    return p


def build_toc(doc, anchor):
    """Write the table of contents into the document, after its own heading.

    Layout is the department exemplar's, measured from it rather than eyeballed: every
    line double-spaced like the body, bold 'Page' head and the folios standing in a
    column that starts at the right margin and runs 1.59 cm into it, no dot leaders,
    chapters bold with a single-spaced blank line between groups.
    """
    pages = _page_map()
    width = Cm(21.0 - 2 * 2.54)
    cur = anchor._p

    def newpar(spacing=2.0):
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.line_spacing = spacing          # the exemplar's contents is double-spaced
        pf.space_before = Pt(0)
        pf.space_after = Pt(0)
        # the folio column begins at the right margin and runs 1.59 cm into it, as the
        # exemplar does; without the negative right indent Word wraps the folio instead
        pf.right_indent = Cm(-1.59)
        pf.tab_stops.add_tab_stop(Cm(1.27), WD_TAB_ALIGNMENT.LEFT)   # number -> title
        pf.tab_stops.add_tab_stop(width, WD_TAB_ALIGNMENT.LEFT)      # -> folio
        return p

    def place(p):
        nonlocal cur
        cur.addnext(p._p)
        cur = p._p
        return p

    head = place(newpar())
    head.paragraph_format.left_indent = width        # "Page" stands at the right margin
    r = head.add_run("Page"); r.bold = True
    r.font.name = "Times New Roman"; r.font.size = Pt(12)

    prev = None
    for e in TOC_ENTRIES:
        if e["level"] == 1 and prev is not None:
            place(newpar(spacing=1.0))            # a blank line opens each chapter
        bold = e["level"] == 1
        place(_folio_par(newpar(), e["label"], pages.get(e["label"], ""), bold))
        prev = e["level"]

# ---------------------------------------------------------------- styling
def force_font(style, name="Times New Roman", size=12, bold=None):
    style.font.name = name
    style.font.size = Pt(size)
    if bold is not None:
        style.font.bold = bold
    style.font.color.rgb = RGBColor(0, 0, 0)
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts"); rpr.append(rfonts)
    for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rfonts.set(qn(a), name)


def setup(doc):
    s = doc.sections[0]
    s.page_width, s.page_height = Cm(21.0), Cm(29.7)
    for m in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(s, m, Cm(2.54))

    normal = doc.styles["Normal"]
    force_font(normal, size=12)
    pf = normal.paragraph_format
    pf.line_spacing = 2.0
    pf.space_after = Pt(0)
    pf.space_before = Pt(0)
    pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    for nm, sz in (("Heading 1", 14), ("Heading 2", 14), ("Heading 3", 12), ("Heading 4", 12)):
        st = doc.styles[nm]
        force_font(st, size=sz, bold=True)
        st.paragraph_format.space_before = Pt(0)
        st.paragraph_format.space_after = Pt(0)
        st.paragraph_format.line_spacing = 2.0
        st.paragraph_format.keep_with_next = True

    guide = doc.styles.add_style("GUIDE NOTE", WD_STYLE_TYPE.PARAGRAPH)
    guide.base_style = doc.styles["Normal"]
    force_font(guide, size=11)
    guide.font.italic = True
    guide.font.color.rgb = RGBColor(0xE6, 0x7E, 0x22)
    guide.paragraph_format.line_spacing = 1.15
    guide.paragraph_format.space_after = Pt(8)
    guide.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT

    cap = doc.styles.add_style("CAPTION TNR", WD_STYLE_TYPE.PARAGRAPH)
    cap.base_style = doc.styles["Normal"]
    force_font(cap, size=12, bold=True)
    cap.paragraph_format.line_spacing = 1.15
    cap.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_before = Pt(6)
    cap.paragraph_format.space_after = Pt(6)
    return doc


CENTER = WD_ALIGN_PARAGRAPH.CENTER
LEFT = WD_ALIGN_PARAGRAPH.LEFT


def add_runs(par, text, bold=False, italic=False):
    """Handle **bold** and *italic* inline markers."""
    for tok in re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*)", text):
        if not tok:
            continue
        b, i = bold, italic
        if tok.startswith("**") and tok.endswith("**"):
            tok, b = tok[2:-2], True
        elif tok.startswith("*") and tok.endswith("*") and len(tok) > 2:
            tok, i = tok[1:-1], True
        r = par.add_run(tok)
        r.bold, r.italic = b, i


def plain(text):
    return re.sub(r"\*+", "", text)

# ---------------------------------------------------------------- front matter
def pagebreak(doc):
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def centred(doc, text, size=12, bold=True, spacing=None, after=0, style=None, new_page=False):
    p = doc.add_paragraph(style=style)
    r = p.add_run(text)
    r.bold = bold
    r.font.size = Pt(size)
    p.alignment = CENTER
    p.paragraph_format.line_spacing = spacing if spacing else 2.0
    p.paragraph_format.space_after = Pt(after)
    if new_page:
        # start the page on the heading itself: a break paragraph of its own can be
        # pushed onto a fresh page when the page before it is full, and prints blank
        p.paragraph_format.page_break_before = True
    return p


def front_matter(doc, figs, tabs):
    m = META
    toc_mark("Title Page", 0, m["title"], centred(doc, m["title"], size=18, spacing=1.5, after=24))
    centred(doc, "BY", size=16, after=12)
    centred(doc, m["name"], size=16, after=6)
    centred(doc, m["matric"], size=16, after=36)
    for line in ("A PROJECT SUBMITTED TO THE", "DEPARTMENT OF COMPUTER SCIENCE",
                 "FACULTY OF SCIENCE AND TECHNOLOGY",
                 "NATIONAL OPEN UNIVERSITY OF NIGERIA"):
        centred(doc, line, size=16, spacing=1.5)
    doc.add_paragraph()
    for line in ("IN PARTIAL FULFILMENT OF THE REQUIREMENTS FOR THE AWARD OF "
                 "BACHELOR OF SCIENCE DEGREE IN", "COMPUTER SCIENCE"):
        centred(doc, line, size=16, spacing=1.5)
    doc.add_paragraph()
    centred(doc, m["date"], size=16, spacing=1.5)

    toc_mark("Declaration", 0, "DECLARATION",
             centred(doc, "DECLARATION", size=14, after=18, new_page=True))
    doc.add_paragraph(
        f"I hereby declare that the work presented in this project is the outcome of the research "
        f"performed by me under the supervision of {m['supervisor']}. Information derived from "
        f"published and unpublished materials has been duly acknowledged in the text and listed in the "
        f"references. This project has not been submitted, in whole or in part, for the award of any "
        f"other degree or diploma of this or any other institution.")
    doc.add_paragraph()
    doc.add_paragraph("______________________________\t\t\t\t__________________")
    doc.add_paragraph(f"{m['name']}\t\t\t\t\t\t\t\tDATE")
    doc.add_paragraph("STUDENT")

    toc_mark("Certification", 0, "CERTIFICATION",
             centred(doc, "CERTIFICATION", size=14, after=18, new_page=True))
    doc.add_paragraph(
        f"I certify that this project work was carried out by {m['name']} of the Department of Computer "
        f"Science with matriculation number {m['matric']} and has satisfactorily completed the "
        f"requirements for the award of Bachelor of Science (B.Sc.) Degree in Computer Science. The work "
        f"embodied in this project has been read and approved as meeting the requirements of the "
        f"Department of Computer Science, Faculty of Science and Technology, National Open University of "
        f"Nigeria.")
    doc.add_paragraph()
    roles = [("(Project Supervisor)", m["supervisor"]),
             ("(Study Centre Director)", ""),
             ("(Dean, Faculty of Science and Technology)", "")]
    for role, who in roles:
        doc.add_paragraph("………………………………\t\t\t\t.......................")
        doc.add_paragraph(f"{who}\t\t\t\t\t\tDATE")
        doc.add_paragraph(role)
        doc.add_paragraph()

    toc_mark("Dedication", 0, "DEDICATION",
             centred(doc, "DEDICATION", size=14, after=18, new_page=True))
    doc.add_paragraph(
        "This project work is dedicated to God Almighty, the source of the strength and clarity that "
        "sustained me throughout this programme, and to my family, whose encouragement made every long "
        "semester possible. Also to my friends that encouraged me to keep going.", style="Normal")

    toc_mark("Acknowledgement", 0, "ACKNOWLEDGEMENT",
             centred(doc, "ACKNOWLEDGEMENT", size=14, after=18, new_page=True))
    doc.add_paragraph(
        "I sincerely appreciate my project supervisor, whose guidance, corrections and insistence on "
        "evidence shaped both this report and the system it describes. I am grateful to the Department of "
        "Computer Science, Faculty of Science and Technology, National Open University of Nigeria, for "
        "the academic foundation and the facilities that supported this work.")
    doc.add_paragraph(
        "I also acknowledge the maintainers of the PhiUSIIL phishing URL dataset and the UCI Machine "
        "Learning Repository, whose openly licensed data made the empirical component of this study "
        "possible, and the Anti-Phishing Working Group, whose published trend reports supplied the "
        "industry context for Chapter One.")

    toc_mark("Abstract", 0, "ABSTRACT",
             centred(doc, "ABSTRACT", size=14, after=18, new_page=True))
    doc.add_paragraph(
        "Phishing is among the most common vectors of financial fraud, and URL-only detection is the only defence that "
        "can answer before a user clicks. This study designed, implemented and evaluated an AI-powered phishing "
        "detection and URL classification tool that classifies an address in under fifteen milliseconds from sixteen "
        "lexical and structural features of the URL string alone. A Random Forest of 200 trees and a Logistic "
        "Regression were trained on the 235,795-record PhiUSIIL dataset on an identical stratified split, the Random "
        "Forest reaching 99.59 per cent accuracy on 47,074 held-out records. On 1,000 unseen addresses from independent "
        "blocklists that accuracy fell to 66.6 per cent. Examining the data rather than the model showed why: every "
        "legitimate record is one URL shape, an HTTPS address beginning with www and carrying no path, while 59.9 per "
        "cent of phishing records carry a path, so the classifier had learned the template of the legitimate class, not "
        "the appearance of an attack. The data was therefore extended with 17,705 legitimate rows from 194 harvested "
        "and 2,024 generated well-known domains. The corrected system reaches 88.44 per cent accuracy on a "
        "7,368-address field test, or 95.48 per cent with a reputation layer that downgrades rather than silences a "
        "conflicting verdict, at a cost of in-dataset accuracy falling to 95.73 per cent. Requiring an accusation to be "
        "supported by the main domain alone took those false accusations from 41.59 to 3.00 per cent, while weakening "
        "36.5 per cent of the hostile accusations met of the same shape, so such cases are shown as unverified rather "
        "than as malicious. Because no Nigerian domain appears in the global top 100,000, a curated list of 99 Nigerian "
        "domains was compiled. For Nigerian users, a locally built detector is only as reliable as the legitimate local "
        "traffic it has been shown.")
    doc.add_paragraph("Key words: phishing detection; URL classification; machine learning; Random Forest; "
                      "dataset bias; Nigerian internet users.")

    toc_par = centred(doc, "TABLE OF CONTENTS", size=14, after=0, new_page=True)
    TOC_ANCHOR.append(toc_par)
    toc_mark("Table of Contents", 0, "TABLE OF CONTENTS", toc_par)

    toc_mark("List of Tables", 0, "LIST OF TABLES",
             centred(doc, "LIST OF TABLES", size=14, after=18, new_page=True))
    for n, cap in enumerate(tabs, 1):
        par = doc.add_paragraph(f"Table {n}:\t{plain(cap)}")
        par.paragraph_format.line_spacing = 1.5

    toc_mark("List of Figures", 0, "LIST OF FIGURES",
             centred(doc, "LIST OF FIGURES", size=14, after=18, new_page=True))
    for n, cap in enumerate(figs, 1):
        par = doc.add_paragraph(f"Figure {n}:\t{plain(cap)}")
        par.paragraph_format.line_spacing = 1.5


# ---------------------------------------------------------------- pagination
def page_field(par):
    """Put a live PAGE field in a paragraph (Word fills the number)."""
    run = par.add_run()
    b = OxmlElement("w:fldChar"); b.set(qn("w:fldCharType"), "begin")
    i = OxmlElement("w:instrText"); i.set(qn("xml:space"), "preserve"); i.text = " PAGE "
    e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), "end")
    run._r.append(b); run._r.append(i); run._r.append(e)
    run.font.name = "Times New Roman"
    run.font.size = Pt(11)


def _pgnum_type(section, fmt, start):
    """w:pgNumType must sit before w:cols / w:docGrid in the sectPr sequence."""
    sectPr = section._sectPr
    for el in sectPr.findall(qn("w:pgNumType")):
        sectPr.remove(el)
    el = OxmlElement("w:pgNumType")
    el.set(qn("w:fmt"), fmt)
    el.set(qn("w:start"), str(start))
    anchor = None
    for tag in ("w:cols", "w:docGrid", "w:vAlign"):
        found = sectPr.find(qn(tag))
        if found is not None:
            anchor = found
            break
    if anchor is not None:
        anchor.addprevious(el)
    else:
        sectPr.append(el)


def number_pages(doc):
    """Front matter in lower-case roman, body from Chapter One in arabic."""
    for idx, section in enumerate(doc.sections):
        footer = section.footer
        footer.is_linked_to_previous = False
        par = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
        par.text = ""
        par.alignment = CENTER
        par.paragraph_format.space_before = Pt(0)
        par.paragraph_format.space_after = Pt(0)
        par.paragraph_format.line_spacing = 1.0
        page_field(par)
        if idx == 0:
            _pgnum_type(section, "lowerRoman", 1)
        else:
            _pgnum_type(section, "decimal", 1)


# ---------------------------------------------------------------- appendix
CODE_FILES = [
    ("APPENDIX A", "Source code of the deployed classification service (app.py).",
     "app.py"),
    ("APPENDIX B", "Source code of the model training and data-correction pipeline (retrain.py).",
     "retrain.py"),
]


def appendix(doc):
    """List the source code the study reports and evaluates, read from disk.

    Reading the deployed files keeps the appendix incapable of drifting from what
    Chapter Four actually measured.
    """
    for title, blurb, rel in CODE_FILES:
        path = os.path.join(HERE, rel)
        if not os.path.exists(path):
            continue
        toc_mark(title, 1, title,
                 centred(doc, title, size=14, style="Heading 1", new_page=True))
        cap = doc.add_paragraph(f"{blurb} {rel.split('/')[-1]} is reproduced in full, "
                                f"as deployed on the day the results in Chapter Four were generated.")
        cap.paragraph_format.line_spacing = 1.5
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        for ln in lines:
            par = doc.add_paragraph()
            pf = par.paragraph_format
            pf.line_spacing = 1.0
            pf.space_before = Pt(0)
            pf.space_after = Pt(0)
            par.alignment = WD_ALIGN_PARAGRAPH.LEFT
            run = par.add_run(ln if ln.strip() else " ")
            run.font.name = "Courier New"
            run.font.size = Pt(8)


# ---------------------------------------------------------------- body
def body(doc, blocks):
    fig_n = tab_n = 0
    chapter_open = False
    in_refs = False
    first_chapter = True
    for idx, (kind, val) in enumerate(blocks):
        nxt = blocks[idx + 1] if idx + 1 < len(blocks) else ("", "")
        if kind == "chapter":
            in_refs = val.strip().upper().startswith("REFERENCE")
        if kind == "chapter":
            if first_chapter:
                # section break: front matter carries roman folios, the body arabic ones
                doc.add_section(WD_SECTION.NEW_PAGE)
                first_chapter = False
                fresh = False
            else:
                fresh = True
            if val.upper().startswith("CHAPTER"):
                par = centred(doc, val.upper(), size=14, style="Heading 1", new_page=fresh)
                title = nxt[1].upper() if nxt[0] == "subtitle" else ""
                toc_mark(f"{val.upper()}: {title}" if title else val.upper(), 1,
                         f"{val.upper()} {title}", par)
                chapter_open = True
            else:
                par = centred(doc, val.upper(), size=14, style="Heading 1", new_page=fresh)
                toc_mark(val.upper(), 1, val.upper(), par)
                chapter_open = False
        elif kind == "subtitle":
            centred(doc, val.upper(), size=14, style="Heading 1")
        elif kind == "section":
            num, _, title = val.partition(" ")
            h = doc.add_paragraph(style="Heading 2")
            r = h.add_run(f"{num}\t{title}")
            r.bold = True
            toc_mark(f"{num} {title}", 2, f"{num} {title}", h)
        elif kind == "subsection":
            num, _, title = val.partition(" ")
            h = doc.add_paragraph(style="Heading 3")
            r = h.add_run(f"{num}\t{title}")
            r.bold = True
        elif kind == "note":
            doc.add_paragraph(val, style="GUIDE NOTE")
        elif kind == "para":
            p = doc.add_paragraph()
            add_runs(p, val)
            if in_refs:
                pf = p.paragraph_format
                pf.left_indent = Cm(1.27)
                pf.first_line_indent = Cm(-1.27)
                pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
        elif kind == "quote":
            p = doc.add_paragraph()
            add_runs(p, val)
            p.paragraph_format.left_indent = Cm(1.27)
        elif kind in ("bullet", "num"):
            p = doc.add_paragraph()
            add_runs(p, val if kind == "num" else "•\t" + val)
            pf = p.paragraph_format
            pf.left_indent = Cm(1.27)
            pf.first_line_indent = Cm(-0.7 if kind == "bullet" else -1.27)
            pf.line_spacing = 2.0
            pf.space_after = Pt(0)
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        elif kind == "fig":
            fig_n += 1
            cap = fig_caption(val)
            path = fig_path(val)
            if path and os.path.exists(path):
                px = png_size(path)
                w_cm = 14.5
                if px:
                    w_cm = min(w_cm, 18.6 * px[0] / px[1])   # cap height at 18.6 cm
                pic = doc.add_paragraph()
                pic.alignment = CENTER
                pf = pic.paragraph_format
                pf.space_before = Pt(12)
                pf.space_after = Pt(6)
                pf.line_spacing = 1.0
                pf.keep_with_next = True
                pic.add_run().add_picture(path, width=Cm(w_cm))
            elif path:
                ph = doc.add_paragraph()
                ph.alignment = CENTER
                r = ph.add_run(f"[MISSING IMAGE: {path}]")
                r.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
            else:
                ph = doc.add_paragraph()
                ph.alignment = CENTER
                r = ph.add_run(f"[{cap} — figure to be inserted]")
                r.bold = False
                r.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
            centred(doc, f"Figure {fig_n}: {plain(cap)}", size=12, style="CAPTION TNR")
        elif kind == "tablecap":
            tab_n += 1
            centred(doc, f"Table {tab_n}: {plain(val)}", size=12, style="CAPTION TNR")
        elif kind == "table":
            rows = val
            t = doc.add_table(rows=len(rows), cols=max(len(r) for r in rows))
            t.style = "Table Grid"
            t.alignment = WD_TABLE_ALIGNMENT.CENTER
            for ri, row in enumerate(rows):
                for ci, cell in enumerate(row):
                    c = t.cell(ri, ci)
                    c.text = ""
                    p = c.paragraphs[0]
                    p.paragraph_format.line_spacing = 1.0
                    p.paragraph_format.space_after = Pt(0)
                    add_runs(p, cell, bold=(ri == 0))
                    for r in p.runs:
                        r.font.size = Pt(11)
                        r.font.name = "Times New Roman"
            doc.add_paragraph()


def main():
    files = sorted(glob.glob(os.path.join(HERE, "ch*.md")))
    blocks = []
    for f in files:
        blocks.extend(parse(f))
    figs, tabs = collect(blocks)
    doc = Document()
    setup(doc)
    front_matter(doc, figs, tabs)
    body(doc, blocks)
    appendix(doc)
    number_pages(doc)
    if TOC_ANCHOR:
        build_toc(doc, TOC_ANCHOR[0])
    doc.save(OUT)
    import json
    with open(os.path.join(HERE, "artifacts", "toc_meta.json"), "w", encoding="utf-8") as fh:
        json.dump([{k: e[k] for k in ("label", "level", "search", "bookmark")} for e in TOC_ENTRIES],
                  fh, indent=1)
    words = sum(len(plain(b[1]).split()) for b in blocks if b[0] in ("para", "bullet", "num"))
    print(f"SAVED {OUT}")
    print(f"body words: {words} | figures: {len(figs)} | tables: {len(tabs)} | files: {[os.path.basename(f) for f in files]}")


if __name__ == "__main__":
    main()