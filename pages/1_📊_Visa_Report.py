import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io

# 1. PAGE SETUP
st.set_page_config(page_title="Visa Report Automator", page_icon="✈️")
st.title("✈️ Weekly Visa Report Automator")
st.write("Upload your raw Agentcis report to generate the 3-tab summary.")

# 2. FILE UPLOADER
uploaded_file = st.file_uploader("Upload CSV or Excel file", type=['csv', 'xlsx'])

if uploaded_file is not None:
    try:
        # Load the file based on extension
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        st.success("File uploaded successfully! Processing...")

        # 3. PROCESSING LOGIC
        # Convert Dates
        df['Visa Expiry Date'] = pd.to_datetime(df['Visa Expiry Date'], errors='coerce')
        
        # Define Timeframe
        today = datetime.now()
        three_months_out = today + timedelta(days=90)
        
        # Filter 1: < 3 Months (Future expiries only)
        # We ensure we don't pick up old expired visas (must be > today)
        mask_time = (df['Visa Expiry Date'] >= today) & (df['Visa Expiry Date'] <= three_months_out)
        df_all = df[mask_time].copy()
        
        # Filter 2: SC 500
        mask_500 = df_all['Visa Type'].astype(str).str.contains("500", na=False)
        df_500 = df_all[mask_500]
        
        # Filter 3: SC 485
        mask_485 = df_all['Visa Type'].astype(str).str.contains("485", na=False)
        df_485 = df_all[mask_485]
        
        # Show quick stats
        col1, col2, col3 = st.columns(3)
        col1.metric("Total < 3 Months", len(df_all))
        col2.metric("SC 500", len(df_500))
        col3.metric("SC 485", len(df_485))

        # 4. SAVE TO EXCEL (IN MEMORY)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_all.to_excel(writer, sheet_name='All < 3 Months', index=False)
            df_500.to_excel(writer, sheet_name='SC 500 < 3 Months', index=False)
            df_485.to_excel(writer, sheet_name='SC 485 < 3 Months', index=False)
            
        # 5. DOWNLOAD BUTTON
        st.download_button(
            label="📥 Download Final Report",
            data=buffer,
            file_name=f"Weekly_Report_{datetime.now().date()}.xlsx",
            mime="application/vnd.ms-excel"
        )

        st.divider()
        st.header("📧 Email Report")

        # --- CONFIGURATION LOGIC ---
        import json
        import os

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
            data = {
                "sender_email": email,
                "sender_password": password,
                "recipients": recipients
            }
            with open(CONFIG_FILE, "w") as f:
                json.dump(data, f)

        config = load_config()
        # ---------------------------

        # Sidebar for credentials
        with st.sidebar:
            st.header("Email Configuration")
            
            # Load defaults from config if available
            default_email = config.get("sender_email", "")
            default_password = config.get("sender_password", "")
            
            sender_email = st.text_input("Sender Email", value=default_email)
            sender_password = st.text_input("App Password", value=default_password, type="password")
            st.info("Use an App Password if using Gmail (2FA enabled).")

        # Email details
        # Load default recipients from config
        default_recipients = config.get("recipients", "fixed_person1@example.com, fixed_person2@example.com")
        recipients = st.text_input("Recipients (comma separated)", value=default_recipients)
        
        # Now we can implement the Save button logic properly since 'recipients' is defined
        with st.sidebar:
             if st.button("💾 Save Configuration"):
                save_config(sender_email, sender_password, recipients)
                st.success("Configuration Saved!")

        email_subject = st.text_input("Subject", f"Weekly Visa Report - {datetime.now().date()}")
        
        default_body = f"""Hi Team,

Please find attached the Weekly Visa Report for {datetime.now().date()}.

Summary:
- Total < 3 Months: {len(df_all)}
- SC 500: {len(df_500)}
- SC 485: {len(df_485)}

Regards,
Ashish Shrestha"""

        email_body = st.text_area("Email Draft", default_body, height=200)

        if st.button("🚀 Send Email"):
            if not sender_email or not sender_password:
                st.error("Please provide Sender Email and App Password in the sidebar.")
            else:
                try:
                    import smtplib
                    from email.mime.multipart import MIMEMultipart
                    from email.mime.text import MIMEText
                    from email.mime.base import MIMEBase
                    from email import encoders

                    # Setup the MIME
                    msg = MIMEMultipart()
                    msg['From'] = sender_email
                    msg['To'] = recipients
                    msg['Subject'] = email_subject

                    msg.attach(MIMEText(email_body, 'plain'))

                    # Attachment
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(buffer.getvalue())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f"attachment; filename= Weekly_Report_{datetime.now().date()}.xlsx")
                    msg.attach(part)

                    # SMTP Session
                    # Assuming Gmail for now, but could be configurable
                    server = smtplib.SMTP('smtp.gmail.com', 587)
                    server.starttls()
                    server.login(sender_email, sender_password)
                    text = msg.as_string()
                    
                    # Handle multiple recipients
                    recipient_list = [r.strip() for r in recipients.split(',')]
                    server.sendmail(sender_email, recipient_list, text)
                    server.quit()

                    st.success(f"Email sent successfully to: {recipients}!")
                    
                except Exception as e:
                    st.error(f"Failed to send email. Error: {e}")
        
    except Exception as e:
        st.error(f"Error processing file: {e}")
