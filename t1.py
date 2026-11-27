
import docx
d = docx.Document("/Users/amarachi/.hermes/cache/scratch/project/test_ch1.docx")
for i,p in enumerate(d.paragraphs):
    t=p.text.strip()
    if t and p.style.name.startswith('Heading'):
        print(f"{i}|{p.style.name}|{t[:70]}")
print("--- sample body runs (bold/italic) ---")
for p in d.paragraphs:
    if 'Anti-Phishing Working Group (2025) describes' in p.text:
        print([ (r.text[:40], r.bold, r.italic) for r in p.runs][:4])
        break
for p in d.paragraphs:
    if p.text.startswith('1.\tTo examine'):
        pf=p.paragraph_format
        print("obj:", p.text[:60], "| indent", pf.left_indent.cm, "hang", pf.first_line_indent.cm)
        break
