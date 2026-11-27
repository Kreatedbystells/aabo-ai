
import docx
d = docx.Document("/Users/amarachi/Downloads/Stella_Project_DRAFT.docx")
print("paras", len(d.paragraphs), "tables", len(d.tables))
heads=[p for p in d.paragraphs if p.style.name.startswith('Heading')]
print("headings", len(heads))
for p in heads[18:]:
    print(" ", p.style.name, "|", p.text[:70])
print("\n--- captions ---")
caps=[p.text for p in d.paragraphs if p.style.name=='CAPTION TNR']
print(len(caps)); [print("  ", c[:80]) for c in caps]
print("\n--- tables dims ---")
for i,t in enumerate(d.tables):
    print(i, len(t.rows), len(t.columns), "|", t.cell(0,0).text[:30])
