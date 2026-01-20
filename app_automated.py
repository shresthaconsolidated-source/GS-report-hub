import pandas as pd
from datetime import datetime, timedelta
import io
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from agentcis_client import AgentcisClient
import os

# Configuration
CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def send_email(sender_email, sender_password, recipients, subject, body, attachment_buffer, filename):
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipients
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain'))

        # Attachment
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment_buffer.getvalue())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename= {filename}")
        msg.attach(part)

        # SMTP Session
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        
        recipient_list = [r.strip() for r in recipients.split(',')]
        server.sendmail(sender_email, recipient_list, text)
        server.quit()
        print(f"Email sent successfully to: {recipients}")
        return True
    except Exception as e:
        print(f"Failed to send email. Error: {e}")
        return False

def run_visa_report(config, progress_callback=None, data_callback=None):
    """
    Runs the visa report automation with the provided configuration.
    Returns a dictionary with status and logs.
    """
    logs = []
    def log(message):
        print(message)
        logs.append(message)
        if progress_callback:
            progress_callback(message)

    log("Starting Visa Report Automation...")
    
    try:
        # 1. Fetch Data
        client = AgentcisClient(config["agentcis_api_token"], config["agentcis_base_url"])
        log("Fetching data (this may take a while)...")
        
        # Pass the log function as the callback
        df = client.fetch_visa_data(limit=None, progress_callback=log, data_callback=data_callback) 
        
        if df.empty:
            log("No data found.")
            return {"success": False, "logs": logs, "message": "No data found."}

        # 2. Process Data
        log("Processing data...")
        df['Visa Expiry Date'] = pd.to_datetime(df['Visa Expiry Date'], errors='coerce')
        
        today = datetime.now()
        three_months_out = today + timedelta(days=90)
        
        # Filter 1: < 3 Months (Future expiries only)
        mask_time = (df['Visa Expiry Date'] >= today) & (df['Visa Expiry Date'] <= three_months_out)
        df_all = df[mask_time].copy()
        
        # Filter 2: SC 500
        mask_500 = df_all['Visa Type'].astype(str).str.contains("500", na=False)
        df_500 = df_all[mask_500]
        
        # Filter 3: SC 485
        mask_485 = df_all['Visa Type'].astype(str).str.contains("485", na=False)
        df_485 = df_all[mask_485]
        
        log(f"Found {len(df_all)} visas expiring in next 3 months.")

        # 3. Generate Excel
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_all.to_excel(writer, sheet_name='All < 3 Months', index=False)
            df_500.to_excel(writer, sheet_name='SC 500 < 3 Months', index=False)
            df_485.to_excel(writer, sheet_name='SC 485 < 3 Months', index=False)
        
        # 4. Send Email
        email_subject = f"Weekly Visa Report - {datetime.now().date()}"
        email_body = f"""Hi Team,

Please find attached the Weekly Visa Report for {datetime.now().date()}.

Summary:
- Total < 3 Months: {len(df_all)}
- SC 500: {len(df_500)}
- SC 485: {len(df_485)}

Regards,
Ashish Shrestha"""

        success = send_email(
            config["sender_email"],
            config["sender_password"],
            config["recipients"],
            email_subject,
            email_body,
            buffer,
            f"Weekly_Report_{datetime.now().date()}.xlsx"
        )
        
        if success:
            log("Automation Complete. Email sent.")
            return {"success": True, "logs": logs, "message": "Email sent successfully!"}
        else:
            log("Failed to send email.")
            return {"success": False, "logs": logs, "message": "Failed to send email. Check credentials."}

    except Exception as e:
        log(f"Error: {str(e)}")
        return {"success": False, "logs": logs, "message": f"Error: {str(e)}"}

if __name__ == "__main__":
    config = load_config()
    run_visa_report(config)
