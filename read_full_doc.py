
from docx import Document
import os

TEMPLATE_PATH = "templates/Employement Contract.docx"

if os.path.exists(TEMPLATE_PATH):
    doc = Document(TEMPLATE_PATH)
    full_text = []
    for p in doc.paragraphs:
        if p.text.strip():
            full_text.append(p.text)
            
    print("\n".join(full_text))
else:
    print("File not found.")
