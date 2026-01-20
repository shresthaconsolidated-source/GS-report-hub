import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io
import json
import os

# 1. PAGE SETUP
st.set_page_config(page_title="COE Report Automator", page_icon="🎓")
st.title("🎓 COE Report Automator")
st.write("Upload your COE report to track student visa/COE expiries.")

# 2. FILE UPLOADER & URL INPUT
st.subheader("📂 Data Source")
data_source = st.radio("Choose data source:", ["Upload File", "Dropbox URL"], horizontal=True)

df = None

if data_source == "Upload File":
    uploaded_file = st.file_uploader("Upload CSV or Excel file", type=['csv', 'xlsx'])
    if uploaded_file:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

else:
    dropbox_url = st.text_input("Paste Dropbox Link", placeholder="https://www.dropbox.com/...")
    if dropbox_url:
        try:
            # Convert to direct download link
            if "dl=0" in dropbox_url:
                direct_url = dropbox_url.replace("dl=0", "dl=1")
            elif "dl=1" not in dropbox_url:
                if "?" in dropbox_url:
                    direct_url = dropbox_url + "&dl=1"
                else:
                    direct_url = dropbox_url + "?dl=1"
            else:
                direct_url = dropbox_url
            
            with st.spinner("Downloading data from Dropbox..."):
                import requests
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
                response = requests.get(direct_url, headers=headers, allow_redirects=True)
                response.raise_for_status()
                
                # Debug: Check if we got an HTML file instead of binary
                content_type = response.headers.get('Content-Type', '')
                if 'text/html' in content_type:
                    st.error("⚠️ Dropbox returned a webpage (Login Page) instead of the file.")
                    st.warning("""
                    **Possible Causes:**
                    1. The link is not public (requires login).
                    2. The link expired.
                    
                    **Solution:**
                    - Open Dropbox, click **Share**, and ensure "Anyone with the link" is selected.
                    - OR: Download the file manually and use the **'Upload File'** option above.
                    """)
                    st.stop()
                
                # Load into pandas
                file_content = io.BytesIO(response.content)
                
                # Try Excel first with explicit engine
                try:
                    df = pd.read_excel(file_content, engine='openpyxl')
                except Exception as e_excel:
                    # If Excel fails, try CSV but keep the Excel error for reporting
                    file_content.seek(0)
                    try:
                        df = pd.read_csv(file_content)
                    except Exception as e_csv:
                        st.error(f"❌ Failed to process file.")
                        with st.expander("See Error Details"):
                            st.write(f"**Excel Error:** {e_excel}")
                            st.write(f"**CSV Error:** {e_csv}")
                        st.stop()
                    
            st.success("✅ Data loaded successfully from Dropbox!")
            
        except Exception as e:
            st.error(f"Error fetching from Dropbox: {e}")

if df is not None:
    try:
        # 3. PROCESSING LOGIC
        # Convert Dates
        # Smart Column Detection
        date_col = None
        
        # 1. Try exact match from known patterns
        candidates = ['COE End Date', 'Visa Expiry Date', 'End Date', 'Expiry Date', 'COE End']
        for c in candidates:
            if c in df.columns:
                date_col = c
                break
        
        # 2. Fuzzy search if not found
        if not date_col:
            for col in df.columns:
                col_lower = str(col).lower()
                if ('date' in col_lower or 'expiry' in col_lower) and ('end' in col_lower or 'coe' in col_lower):
                    date_col = col
                    break
        
        if date_col:
            df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
            
            # Define Timeframe (e.g., expiring in next 6 months)
            today = datetime.now()
            six_months_out = today + timedelta(days=180)
            
            # Filter: Expiring soon (future dates only)
            mask_time = (df[date_col] >= today) & (df[date_col] <= six_months_out)
            df_expiring = df[mask_time].copy()
            
            # Show stats
            col1, col2 = st.columns(2)
            col1.metric("Total Students", len(df))
            col2.metric("Expiring < 6 Months", len(df_expiring))
            
            st.divider()
            
            st.subheader("⚠️ Students with Expiring COEs")
            if not df_expiring.empty:
                st.dataframe(df_expiring)
            else:
                st.info("No COEs expiring in the next 6 months.")
                
            # 4. SAVE TO EXCEL (IN MEMORY)
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='All Students', index=False)
                if not df_expiring.empty:
                    df_expiring.to_excel(writer, sheet_name='Expiring Soon', index=False)
                
            # 5. DOWNLOAD BUTTON
            st.download_button(
                label="📥 Download COE Report",
                data=buffer,
                file_name=f"COE_Report_{datetime.now().date()}.xlsx",
                mime="application/vnd.ms-excel"
            )
            
            st.divider()
            
            # --- EMAIL SECTION (Reused Logic) ---
            st.header("📧 Email Report")
            
            CONFIG_FILE = "config.json"

            def load_config():
                if os.path.exists(CONFIG_FILE):
                    try:
                        with open(CONFIG_FILE, "r") as f:
                            return json.load(f)
                    except:
                        return {}
                return {}

            def save_config(email, password, recipients):
                config_data = load_config() # Load existing to update
                config_data["sender_email"] = email
                config_data["sender_password"] = password
                config_data["coe_recipients"] = recipients # Separate recipients for COE
                with open(CONFIG_FILE, "w") as f:
                    json.dump(config_data, f)

            config = load_config()
            
            with st.sidebar:
                st.header("Email Configuration")
                default_email = config.get("sender_email", "")
                default_password = config.get("sender_password", "")
                
                sender_email = st.text_input("Sender Email", value=default_email, key="coe_email")
                sender_password = st.text_input("App Password", value=default_password, type="password", key="coe_pass")
                st.info("Shared credentials with Visa Report.")

            default_recipients = config.get("coe_recipients", "")
            recipients = st.text_input("Recipients (comma separated)", value=default_recipients, key="coe_recipients")
            
            with st.sidebar:
                if st.button("💾 Save Configuration"):
                    save_config(sender_email, sender_password, recipients)
                    st.success("Configuration Saved!")

            email_subject = st.text_input("Subject", f"Weekly COE Report - {datetime.now().date()}")
            
            default_body = f"""Hi Team,

Please find attached the COE Report for {datetime.now().date()}.

Summary:
- Total Students: {len(df)}
- Expiring < 6 Months: {len(df_expiring)}

Regards,
Report Automator"""

            email_body = st.text_area("Email Draft", default_body, height=200)

            if st.button("🚀 Send Email"):
                if not sender_email or not sender_password:
                    st.error("Please configure email settings in the sidebar")
                else:
                    try:
                        import smtplib
                        from email.mime.multipart import MIMEMultipart
                        from email.mime.text import MIMEText
                        from email.mime.base import MIMEBase
                        from email import encoders

                        msg = MIMEMultipart()
                        msg['From'] = sender_email
                        msg['To'] = recipients
                        msg['Subject'] = email_subject

                        msg.attach(MIMEText(email_body, 'plain'))

                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(buffer.getvalue())
                        encoders.encode_base64(part)
                        part.add_header('Content-Disposition', f"attachment; filename=COE_Report_{datetime.now().date()}.xlsx")
                        msg.attach(part)

                        server = smtplib.SMTP('smtp.gmail.com', 587)
                        server.starttls()
                        server.login(sender_email, sender_password)
                        
                        recipient_list = [r.strip() for r in recipients.split(',')]
                        server.sendmail(sender_email, recipient_list, msg.as_string())
                        server.quit()

                        st.success(f"Email sent successfully to: {recipients}!")
                    except Exception as e:
                        st.error(f"Failed to send email. Error: {e}")

        else:
            st.error("Could not find a 'Date' column in the uploaded file. Please ensure there is a column like 'COE End Date'.")
            st.write("Available columns:", df.columns.tolist())

    except Exception as e:
        st.error(f"Error processing file: {e}")
