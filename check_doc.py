
from docx import Document
from docx.shared import Cm
d = Document("/Users/amarachi/Downloads/Stella_Project_DRAFT.docx")
print("inline images:", len(d.inline_shapes))
missing = [p.text for p in d.paragraphs if "MISSING IMAGE" in p.text or "figure to be inserted" in p.text]
print("missing placeholders:", missing)
caps = [p.text for p in d.paragraphs if p.text.startswith("Figure ")]
print("captions:", len(caps))
for c in caps: print("  ", c[:95])
sizes = sorted({(round(s.width.cm,1), round(s.height.cm,1)) for s in d.inline_shapes})
print("image sizes (cm):", sizes)
import os; print("size MB:", round(os.path.getsize("/Users/amarachi/Downloads/Stella_Project_DRAFT.docx")/1e6,1))
