import streamlit as st
import pandas as pd
import os
import io
import requests
from docx import Document
import re

st.set_page_config(page_title="HR Document Generator", page_icon="📝", layout="wide")

st.title("📝 HR Document Generator")
st.markdown("Generate official Profit / Experience letters linked to live Notion data.")

# API Configuration
API_URL = "https://hr-api.ashishoct34.workers.dev/api/hr"

# --- HELPER FUNCTIONS ---
def get_employees():
    """Fetch employees from Cloudflare Worker"""
    try:
        data = requests.get(API_URL).json()
        return data.get('employees', [])
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return []

def fill_template(template_path, data):
    """Replace placeholders in docx"""
    doc = Document(template_path)
    
    # Helper to replace text in a paragraph
    def replace_text(paragraph):
        for key, value in data.items():
            placeholder = f"{{{{{key}}}}}" # {{Key}}
            if placeholder in paragraph.text:
                # Naive replacement (might break formatting if split across runs, 
                # but python-docx-template is better - using simple replace for now)
                # For better results in future we can use 'docxtpl' library
                paragraph.text = paragraph.text.replace(placeholder, str(value))
    
    # Scan Paragraphs
    for p in doc.paragraphs:
        replace_text(p)
        
    # Scan Tables
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    replace_text(p)
                    
    # Save to buffer
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- 1. LOAD DATA ---
with st.spinner("Fetching employee data from Notion..."):
    employees = get_employees()

if not employees:
    st.stop()

# --- 2. SELECT EMPLOYEE ---
employee_names = [e.get('name', 'Unknown') for e in employees]
selected_name = st.selectbox("👤 Select Employee", employee_names)

# Get full employee object
employee = next((e for e in employees if e['name'] == selected_name), None)

if employee:
    # --- 3. SHOW DETAILS ---
    with st.expander("📄 View Employee Details", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write(f"**Name:** {employee.get('name')}")
            st.write(f"**ID:** {employee.get('employee_id', 'N/A')}")
            st.write(f"**Role:** {employee.get('role', 'N/A')}")
        with col2:
            st.write(f"**Join Date:** {employee.get('join_date', 'N/A')}")
            st.write(f"**Gender:** {employee.get('gender', 'N/A')}")
            st.write(f"**Department:** {employee.get('department', 'N/A')}")
        with col3:
             st.write(f"**Status:** {employee.get('status', 'N/A')}")
             st.write(f"**Email:** {employee.get('email', 'N/A')}")

    st.divider()

    # --- 4. GENERATE DOCUMENTS ---
    col_sal, col_exp = st.columns(2)
    
    TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")
    
    # MAPPING LOGIC (Map API keys to Template {{Keys}})
    # You can adjust these keys based on what you put in the Word doc
    template_data = {
        "Name": employee.get('name', ''),
        "EmployeeID": employee.get('employee_id', ''),
        "Role": employee.get('role', ''),
        "JoinDate": employee.get('join_date', ''),
        "Salary": employee.get('last_salary', '0'), # Raw value
        "Department": employee.get('department', ''),
        # Add generated fields
        "Date": pd.Timestamp.now().strftime('%d-%m-%Y')
    }

    with col_sal:
        st.subheader("💰 Salary Certificate")
        st.write("Generates certificate using standard salary template.")
        
        # Check for template
        sal_template = "Salary Certificate.docx"
        sal_path = os.path.join(TEMPLATE_DIR, sal_template)
        
        if os.path.exists(sal_path):
            if st.button("Generate Salary Certificate"):
                doc_buffer = fill_template(sal_path, template_data)
                
                st.download_button(
                    label="⬇️ Download DOCX",
                    data=doc_buffer,
                    file_name=f"Salary_Certificate_{employee['name']}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
        else:
            st.error(f"Template '{sal_template}' not found.")

    with col_exp:
        st.subheader("📜 Experience Letter")
        
        responsibilities = st.text_area("Key Tasks & Responsibilities", height=150, placeholder="• Led the marketing team\n• Managed budget of $50k...")
        
        # Add responsibilities to data
        exp_data = template_data.copy()
        exp_data["Responsibilities"] = responsibilities
        
        exp_template = "Experience Letter.docx" # You might need to rename your uploaded file to match this
        exp_path = os.path.join(TEMPLATE_DIR, exp_template)
        
        if os.path.exists(exp_path):
             if st.button("Generate Experience Letter"):
                doc_buffer = fill_template(exp_path, exp_data)
                
                st.download_button(
                    label="⬇️ Download DOCX",
                    data=doc_buffer,
                    file_name=f"Experience_Letter_{employee['name']}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
        else:
            st.error(f"Template '{exp_template}' not found. Please rename your uploaded file to 'Experience Letter.docx'")

    st.info("ℹ️ **Note:** Ensure your Word templates have placeholders like `{{Name}}`, `{{Role}}`, `{{Responsibilities}}`.")



