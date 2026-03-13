import os
from docx import Document

def _clear_paragraph(p):
    """Helper to clear text from a paragraph without losing its formatting"""
    if len(p.runs) > 0:
        for run in p.runs:
            run.text = ""

def _replace_paragraph_text(p, text):
    """Helper to safely replace paragraph text preserving existing style of the first run"""
    _clear_paragraph(p)
    if len(p.runs) > 0:
        p.runs[0].text = text
    else:
        p.add_run(text)

def generate_invoice(supplier, invoice_date, invoice_no, period_str, amount, output_path):
    # Absolute path logic to find the template if executed from root or within pages
    base_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(base_dir, "templates", "rcti_template.docx")
    
    if not os.path.exists(template_path):
        # Fallback if working dir is not repo root
        template_path = os.path.join(os.getcwd(), "templates", "rcti_template.docx")
        if not os.path.exists(template_path):
             raise FileNotFoundError(f"Template not found at {template_path}")

    doc = Document(template_path)
    
    # We mapped these paragraph indexes previously
    # Paragraph 6: Date: 24 Oct 2025
    _replace_paragraph_text(doc.paragraphs[6], f"Date: {invoice_date}")
    
    # Paragraph 7: Invoice No: RCTI_SC_27
    _replace_paragraph_text(doc.paragraphs[7], f"Invoice No: RCTI_SC_{invoice_no}")
    
    # Paragraph 8: To Supplier : Eve Miringching Magar
    _replace_paragraph_text(doc.paragraphs[8], f"To Supplier : {supplier['name']}")
    
    # Paragraph 10: Supplier ABN : 37 836 121 282
    _replace_paragraph_text(doc.paragraphs[10], f"Supplier ABN : {supplier['abn']}")
    
    # Paragraph 11: Address : 2/27 Cypress Street Adelaide SA 4000
    _replace_paragraph_text(doc.paragraphs[11], f"Address : {supplier['address']}")
    
    # Paragraph 12: Phone: 0452 106 335
    _replace_paragraph_text(doc.paragraphs[12], f"Phone: {supplier['phone']}")
    
    # Paragraph 18: Bank Name: Commonwealth Bank
    _replace_paragraph_text(doc.paragraphs[18], f"Bank Name: {supplier['bank_name']}")
    
    # Paragraph 19: BSB No: 065-000
    _replace_paragraph_text(doc.paragraphs[19], f"BSB No: {supplier['bsb']}")
    
    # Paragraph 20: Account Number: 1262 8218
    _replace_paragraph_text(doc.paragraphs[20], f"Account Number: {supplier['account_number']}")
    
    # Table Modification
    table = doc.tables[0]
    
    # Table 0 Row 1 Col 0: Description
    desc_text = f"Subcontractor service to Global Select Education and Migration Pty Ltd\n({period_str})"
    _replace_paragraph_text(table.cell(1, 0).paragraphs[0], desc_text)
    
    amount_str = f"{float(amount):,.0f}" if float(amount).is_integer() else f"{float(amount):,.2f}"
    
    # Table 0 Row 1 Col 1: Amount
    _replace_paragraph_text(table.cell(1, 1).paragraphs[0], amount_str)
    
    # Table 0 Row 2 Col 1: Total amount
    _replace_paragraph_text(table.cell(2, 1).paragraphs[0], amount_str)

    doc.save(output_path)
    return output_path

if __name__ == "__main__":
    # Test
    supplier = {
        "name": "TEMPLATE TEST USER",
        "abn": "99 999 999 999",
        "address": "123 Fake Street, Space",
        "phone": "0400 000 000",
        "bank_name": "Test Bank",
        "bsb": "123-456",
        "account_number": "987654321"
    }
    generate_invoice(supplier, "30 Dec 2026", "999", "1 Dec 2026 to 14 Dec 2026", 2500.0, "test_template.docx")
    print("Generated test_template.docx")
