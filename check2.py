
from docx import Document
from docx.oxml.ns import qn
d = Document("/Users/amarachi/Downloads/Stella_Project_DRAFT.docx")
body = d.element.body
seq = []
for child in body.iterchildren():
    if child.tag == qn("w:p"):
        txt = "".join(t.text or "" for t in child.iter(qn("w:t")))
        has_img = child.find(".//" + qn("w:drawing")) is not None
        seq.append(("IMG" if has_img else "P", txt.strip()))
bad = []
for i, (k, t) in enumerate(seq):
    if k == "IMG":
        nxt = next((s for s in seq[i+1:] if s[1]), None)
        if not nxt or not nxt[1].startswith("Figure "):
            bad.append((i, t[:40], nxt))
print("images:", sum(1 for k,_ in seq if k=="IMG"))
print("images without an immediate caption:", len(bad))
for b in bad[:5]: print("  ", b)
# per-chapter word counts
import re
words = 0; counts = {}
cur = None
for k, t in seq:
    if k == "P" and t.upper().startswith("CHAPTER "):
        cur = t.upper(); counts[cur] = 0
    elif cur and k == "P":
        counts[cur] += len(t.split())
print(counts)
print("total words", sum(len(t.split()) for k,t in seq))
