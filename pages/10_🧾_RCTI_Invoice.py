import streamlit as st
import json
import os
import uuid
from invoice_generator import generate_invoice
from datetime import datetime

SUPPLIERS_FILE = 'suppliers.json'

def load_suppliers():
    if not os.path.exists(SUPPLIERS_FILE):
        return []
    with open(SUPPLIERS_FILE, 'r') as f:
        return json.load(f)

def save_suppliers(suppliers):
    with open(SUPPLIERS_FILE, 'w') as f:
        json.dump(suppliers, f, indent=2)

st.set_page_config(page_title="RCTI Invoice Generator", layout="centered")

st.title("🧾 RCTI Invoice Generator")

suppliers = load_suppliers()

st.sidebar.header("Supplier Management")

# Management Mode
mgr_mode = st.sidebar.radio("Action", ["Select Supplier", "Add New Supplier", "Edit Supplier", "Delete Supplier"])

supplier_options = {s['id']: f"{s['name']} (ABN: {s['abn']})" for s in suppliers}

selected_supplier_id = None
if suppliers and mgr_mode in ["Select Supplier", "Edit Supplier", "Delete Supplier"]:
    selected_supplier_id = st.sidebar.selectbox("Choose Supplier", options=list(supplier_options.keys()), format_func=lambda x: supplier_options[x], key="supplier_select")

# Add/Edit UI
if mgr_mode == "Add New Supplier":
    st.sidebar.subheader("New Supplier Details")
    with st.sidebar.form("add_supplier_form"):
        new_name = st.text_input("Name")
        new_abn = st.text_input("ABN")
        new_address = st.text_input("Address")
        new_phone = st.text_input("Phone")
        new_bank_name = st.text_input("Bank Name")
        new_bsb = st.text_input("BSB No")
        new_acct = st.text_input("Account Number")
        if st.form_submit_button("Save Supplier"):
            if new_name and new_abn:
                suppliers.append({
                    "id": str(uuid.uuid4()),
                    "name": new_name,
                    "abn": new_abn,
                    "address": new_address,
                    "phone": new_phone,
                    "bank_name": new_bank_name,
                    "bsb": new_bsb,
                    "account_number": new_acct
                })
                save_suppliers(suppliers)
                st.sidebar.success("Supplier Added!")
                st.rerun()
            else:
                st.sidebar.error("Name and ABN are required.")

elif mgr_mode == "Edit Supplier" and selected_supplier_id:
    supplier = next(s for s in suppliers if s['id'] == selected_supplier_id)
    st.sidebar.subheader(f"Edit {supplier['name']}")
    with st.sidebar.form("edit_supplier_form"):
        edit_name = st.text_input("Name", value=supplier['name'])
        edit_abn = st.text_input("ABN", value=supplier['abn'])
        edit_address = st.text_input("Address", value=supplier['address'])
        edit_phone = st.text_input("Phone", value=supplier['phone'])
        edit_bank_name = st.text_input("Bank Name", value=supplier['bank_name'])
        edit_bsb = st.text_input("BSB No", value=supplier['bsb'])
        edit_acct = st.text_input("Account Number", value=supplier['account_number'])
        if st.form_submit_button("Update Supplier"):
            supplier.update({
                "name": edit_name,
                "abn": edit_abn,
                "address": edit_address,
                "phone": edit_phone,
                "bank_name": edit_bank_name,
                "bsb": edit_bsb,
                "account_number": edit_acct
            })
            save_suppliers(suppliers)
            st.sidebar.success("Supplier Updated!")
            st.rerun()

elif mgr_mode == "Delete Supplier" and selected_supplier_id:
    supplier = next(s for s in suppliers if s['id'] == selected_supplier_id)
    st.sidebar.warning(f"Are you sure you want to delete {supplier['name']}?")
    if st.sidebar.button("Yes, Delete"):
        suppliers = [s for s in suppliers if s['id'] != selected_supplier_id]
        save_suppliers(suppliers)
        st.sidebar.success("Supplier Deleted!")
        st.rerun()

# Main UI for Invoice Generation
if mgr_mode == "Select Supplier":
    if not suppliers:
        st.info("Please add a supplier from the sidebar to generate an invoice.")
    elif selected_supplier_id:
        supplier = next(s for s in suppliers if s['id'] == selected_supplier_id)
        
        st.subheader("Invoice Details")
        
        col1, col2 = st.columns(2)
        with col1:
            inv_date = st.date_input("Invoice Date", value="today")
            # Convert date to 12 Oct 2025 format
            inv_date_str = inv_date.strftime("%d %b %Y")
        
        with col2:
            inv_no_input = st.text_input("Invoice No", placeholder="e.g., 27")
            # Enforce digits
            if inv_no_input and not inv_no_input.isdigit():
                st.warning("Invoice No should be numbers only.")
        
        st.markdown("**Invoice Number will prefix with:** `RCTI_SC_`")
        
        col3, col4 = st.columns(2)
        with col3:
            period_start = st.date_input("Fortnight Start Date", value="today")
        with col4:
            period_end = st.date_input("Fortnight End Date", value="today")
            
        period_str = f"{period_start.strftime('%d %b %Y')} to {period_end.strftime('%d %b %Y')}"
        
        amount = st.number_input("Amount (AUD)", min_value=0.0, format="%.2f", step=100.0)
        
        st.markdown("---")
        st.subheader("Preview")
        
        st.markdown(f"**Supplier:** {supplier['name']}")
        st.markdown(f"**Date:** {inv_date_str}")
        st.markdown(f"**Invoice No:** RCTI_SC_{inv_no_input}")
        st.markdown(f"**Period:** {period_str}")
        st.markdown(f"**Amount:** ${amount:,.2f}")
        
        if st.button("Generate Invoice", type="primary"):
            if not inv_no_input.isdigit():
                st.error("Please enter a valid numeric Invoice Number.")
            elif amount <= 0:
                st.error("Please enter a valid amount greater than 0.")
            else:
                try:
                    filename = f"RCTI_SC_{inv_no_input}_{supplier['name'].replace(' ', '_')}.docx"
                    output_path = os.path.join(os.getcwd(), filename)
                    generate_invoice(
                        supplier=supplier,
                        invoice_date=inv_date_str,
                        invoice_no=inv_no_input,
                        period_str=period_str,
                        amount=amount,
                        output_path=output_path
                    )
                    
                    with open(output_path, "rb") as f:
                        file_data = f.read()
                        
                    st.success("Invoice generated successfully!")
                    st.download_button(
                        label="⬇️ Download Invoice Document",
                        data=file_data,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                except Exception as e:
                    st.error(f"Error generating invoice: {e}")
