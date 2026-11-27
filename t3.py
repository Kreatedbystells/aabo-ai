
import docx
d = docx.Document("/Users/amarachi/Downloads/Stella_Project_DRAFT.docx")
txt=[p.text for p in d.paragraphs]
i = next(k for k,t in enumerate(txt) if t.strip()=="LIST OF TABLES")
print("\n".join(txt[i:i+14]))
j = next(k for k,t in enumerate(txt) if t.strip()=="LIST OF FIGURES")
print("---"); print("\n".join(txt[j:j+9]))
print("--- asterisks leaked:", sum(1 for t in txt if "**" in t or ("*" in t and not t.startswith("[") )))
print("--- notes:", sum(1 for p in d.paragraphs if p.style.name=='GUIDE NOTE'))
