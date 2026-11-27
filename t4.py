
import docx
d = docx.Document("/Users/amarachi/Downloads/Stella_Project_DRAFT.docx")
txt=[p.text for p in d.paragraphs]
i = next(k for k,t in enumerate(txt) if t.strip()=="REFERENCES")
print("refs heading at", i, "of", len(txt))
print("--- first 3 refs ---")
n=0
for p in d.paragraphs[i+1:]:
    if p.text.strip():
        pf=p.paragraph_format
        print(p.text[:80], "| hang:", round(pf.first_line_indent.cm,2), "left:", round(pf.left_indent.cm,2))
        n+=1
        if n>=3: break
print("total ref paragraphs:", sum(1 for p in d.paragraphs[i+1:] if p.text.strip()))
print("last para:", txt[-1][:80])
print("--- files ---")
import glob, os
print(sorted(os.path.basename(f) for f in glob.glob(os.path.join('~/.hermes/cache/scratch/project/artifacts','*')))[:12])
