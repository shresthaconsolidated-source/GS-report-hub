import streamlit as st
import json
import os
import sys
import pandas as pd
from datetime import datetime
from app_automated import run_visa_report

# Page Config
st.set_page_config(page_title="Visa Automation Control Panel", page_icon="⚙️", layout="wide")

CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

st.title("⚙️ Visa Automation Control Panel")

# Load Config
config = load_config()

# Tabs
tab1, tab2, tab3 = st.tabs(["🚀 Run Report", "🛠️ Settings", "📅 Schedule"])

# --- TAB 1: RUN REPORT ---
with tab1:
    st.header("Manual Trigger")
    st.write("Click the button below to fetch data from Agentcis and email the report immediately.")
    
    if st.button("▶️ Run Report Now", type="primary"):
        with st.status("Running Automation...", expanded=True) as status:
            log_container = st.empty()
            table_container = st.empty()
            
            all_preview_data = []
            
            def dashboard_log(message):
                log_container.text(f"⏳ {message}")
                
            def dashboard_data(batch):
                all_preview_data.extend(batch)
                # Show last 100 items to avoid UI lag, or all if small
                df_preview = pd.DataFrame(all_preview_data)
                table_container.dataframe(df_preview.tail(100), use_container_width=True)
            
            # Run the automation
            result = run_visa_report(config, progress_callback=dashboard_log, data_callback=dashboard_data)
            
            # Final logs display
            log_text = "\n".join(result.get("logs", []))
            st.text_area("Execution Logs", log_text, height=200)
            
            if result.get("success"):
                status.update(label="✅ Automation Complete!", state="complete", expanded=False)
                st.success(result.get("message"))
            else:
                status.update(label="❌ Automation Failed", state="error", expanded=True)
                st.error(result.get("message"))

# --- TAB 2: SETTINGS ---
with tab2:
    st.header("Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Agentcis API")
        api_token = st.text_input("API Token", value=config.get("agentcis_api_token", ""), type="password")
        base_url = st.text_input("Base URL", value=config.get("agentcis_base_url", "https://globalselect.agentcisapp.com"))
        
    with col2:
        st.subheader("Email Credentials")
        sender_email = st.text_input("Sender Email", value=config.get("sender_email", ""))
        sender_password = st.text_input("App Password", value=config.get("sender_password", ""), type="password")
        
    st.subheader("Report Settings")
    recipients = st.text_area("Recipients (comma separated)", value=config.get("recipients", ""))
    
    if st.button("💾 Save Settings"):
        new_config = {
            "agentcis_api_token": api_token,
            "agentcis_base_url": base_url,
            "sender_email": sender_email,
            "sender_password": sender_password,
            "recipients": recipients
        }
        save_config(new_config)
        st.success("Settings saved successfully!")
        # Reload config to ensure consistency
        config = load_config()

# --- TAB 3: SCHEDULE ---
with tab3:
    st.header("Schedule Automation")
    st.write("Configure the automation to run automatically in the background.")
    
    import subprocess
    
    TASK_NAME = "VisaReportAutomator"
    python_path = sys.executable
    script_path = os.path.abspath("app_automated.py")
    
    # Check status
    def is_task_scheduled():
        try:
            # Check if task exists
            cmd = f'schtasks /Query /TN "{TASK_NAME}"'
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            return result.returncode == 0
        except:
            return False

    is_scheduled = is_task_scheduled()
    
    if is_scheduled:
        st.success(f"✅ Automation is currently **ENABLED**.")
        if st.button("Disable Schedule", type="primary"):
            cmd = f'schtasks /Delete /TN "{TASK_NAME}" /F'
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            if result.returncode == 0:
                st.success("Schedule disabled successfully!")
                st.rerun()
            else:
                st.error(f"Failed to disable: {result.stderr}")
    else:
        st.warning("⚠️ Automation is currently **DISABLED**.")
        
        col1, col2 = st.columns(2)
        with col1:
            day = st.selectbox("Day of Week", ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"], index=0)
        with col2:
            time = st.time_input("Time", value=datetime.strptime("09:00", "%H:%M").time())
            
        if st.button("Enable Schedule"):
            time_str = time.strftime("%H:%M")
            # Create task
            # /SC WEEKLY /D <DAY> /ST <TIME> /TR "<PYTHON> <SCRIPT>" /RL HIGHEST
            # Note: /RL HIGHEST might require admin, but usually standard user can create tasks for themselves
            
            # We wrap the command in quotes to handle spaces in paths
            action = f'"{python_path}" "{script_path}"'
            
            cmd = f'schtasks /Create /SC WEEKLY /D {day} /TN "{TASK_NAME}" /TR "\'{python_path}\' \'{script_path}\'" /ST {time_str} /F'
            
            # Use subprocess to run
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            
            if result.returncode == 0:
                st.success("Schedule enabled successfully!")
                st.rerun()
            else:
                st.error(f"Failed to enable schedule. Error: {result.stderr}")
                st.info("Try running the dashboard as Administrator if permission is denied.")
                st.code(cmd, language="powershell")
