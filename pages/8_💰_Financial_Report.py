import streamlit as st
import pandas as pd
from datetime import datetime
import io
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import requests

# 1. PAGE SETUP
st.set_page_config(page_title="Financial Report", page_icon="💰", layout="wide")

SHEET_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vSbLilDFS9QkZu0nGo1LrgYW8yuE1ZCPuBtv4phS4_JuG2QK29aLRr3_6OcLo-nxE_H8koFHmjpo3qx/pub?gid=46034363&single=true&output=csv'

@st.cache_data(ttl=600)
def load_data():
    return pd.read_csv(SHEET_URL)

def parse_amount(val):
    if isinstance(val, (int, float)): return val
    if isinstance(val, str):
        return float(val.replace(',', ''))
    return 0

def format_currency(val):
    return f"NPR {val:,.2f}"

st.title("💰 Financial Report & Email Generator")
st.write("Live financial overview from Google Sheets with automated email generation.")

# 2. DATA PROCESSING
try:
    df = load_data()
    
    # Pre-process
    df['Txn Date (Cash Basis)'] = pd.to_datetime(df['Txn Date (Cash Basis)'], errors='coerce')
    df['Amount (NPR)'] = df['Amount (NPR)'].apply(parse_amount)
    df['MonthKey'] = df['Txn Date (Cash Basis)'].dt.to_period('M')

    # --- Opening Balances ---
    # Assuming Opening Balances are static or in the first few rows independently.
    # We'll extract them once.
    opening_balances = {
        'NMB': 0,
        'NBL': 0,
        'Petty Cash': 0
    }
    
    # Scan for opening balances (naive: first non-null occurrence)
    for index, row in df.iterrows():
        acc = row.get('Account Name')
        bal = row.get('Opening Balance (AUD)')
        if acc in opening_balances and pd.notna(bal) and opening_balances[acc] == 0:
            opening_balances[acc] = parse_amount(bal)

    # 3. CONTROLS
    all_months = sorted(df['MonthKey'].dropna().unique(), reverse=True)
    
    col_ctrl, col_refresh = st.columns([3, 1])
    with col_ctrl:
        selected_month = st.selectbox("Select Month", all_months)
    
    with col_refresh:
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()

    # 4. CALCULATIONS
    
    # Helper to calc current standing up to end of selected month
    def get_balances_at_month_end(target_month):
        bals = opening_balances.copy()
        
        # Filter all transactions UP TO end of target month
        mask = df['MonthKey'] <= target_month
        sub_df = df[mask]
        
        for _, row in sub_df.iterrows():
            amt = abs(row['Amount (NPR)']) # Logic uses absolute flows
            to_acc = row['To Account']
            from_acc = row['From Account']
            
            if to_acc in bals: bals[to_acc] += amt
            if from_acc in bals: bals[from_acc] -= amt
            
        return bals

    # Helper to calc monthly metrics
    def get_monthly_metrics(month):
        mask = df['MonthKey'] == month
        sub = df[mask]
        
        expenses = 0
        income = 0
        wise = 0
        exp_brk = {}
        wise_brk = {}
        inc_brk = {} # New Income Breakdown
        
        for _, row in sub.iterrows():
            amt = parse_amount(row['Amount (NPR)'])
            abs_amt = abs(amt)
            to_acc = row['To Account']
            from_acc = row['From Account']
            cat = row.get('Category', '') or 'Other'
            desc = str(row.get('Description', ''))
            
            # Expenses
            if to_acc == 'Expense':
                expenses += abs_amt
                exp_brk[cat] = exp_brk.get(cat, 0) + abs_amt
            
            # Income
            if from_acc == 'Income':
                income += amt
                # Breakdown by Category (e.g. IELTS, Commission)
                inc_brk[cat] = inc_brk.get(cat, 0) + amt
                
            # Wise
            if from_acc == 'Wise':
                wise += amt
                # Logic: Categorize
                w_cat = 'Other'
                txt = (str(cat) + ' ' + desc).lower()
                if 'sales' in txt: w_cat = 'Sales'
                elif 'ielts' in txt: w_cat = 'IELTS'
                elif 'commission' in txt: w_cat = 'Commission'
                # Fallback to category if it's not generic 'Transfer'
                elif cat and cat != 'Transfer': w_cat = cat
                
                wise_brk[w_cat] = wise_brk.get(w_cat, 0) + amt
                
        return {
            'expenses': expenses,
            'income': income,
            'wise': wise,
            'expense_breakdown': exp_brk,
            'wise_breakdown': wise_brk,
            'income_breakdown': inc_brk,
            'net_balance': income - expenses
        }

    curr_metrics = get_monthly_metrics(selected_month)
    curr_balances = get_balances_at_month_end(selected_month)

    # Comparison (Previous Month)
    prev_month = selected_month - 1
    prev_metrics = get_monthly_metrics(prev_month)
    
    def get_diff(curr, prev):
        if prev == 0: return 0
        return ((curr - prev) / prev) * 100

    diff_exp = get_diff(curr_metrics['expenses'], prev_metrics['expenses'])
    diff_inc = get_diff(curr_metrics['income'], prev_metrics['income'])
    diff_wise = get_diff(curr_metrics['wise'], prev_metrics['wise'])

    # 5. DASHBOARD UI
    c1, c2, c3 = st.columns(3)
    c1.metric("Global Expenses", format_currency(curr_metrics['expenses']), f"{diff_exp:.1f}%", delta_color="inverse")
    c2.metric("Total Income", format_currency(curr_metrics['income']), f"{diff_inc:.1f}%")
    c3.metric("Transfer from Wise", format_currency(curr_metrics['wise']), f"{diff_wise:.1f}%")

    st.divider()

    col_bal, col_brk = st.columns([1, 1])
    
    with col_bal:
        st.subheader("🏦 Ending Balances")
        st.info(f"Balances as of end of: **{selected_month.strftime('%B %Y')}**")
        bal_df = pd.DataFrame(curr_balances.items(), columns=['Account', 'Balance'])
        bal_df['Balance'] = bal_df['Balance'].apply(format_currency)
        st.dataframe(bal_df, hide_index=True, use_container_width=True)
        
    with col_brk:
        st.subheader("📉 Top Expenses")
        exp_df = pd.DataFrame(curr_metrics['expense_breakdown'].items(), columns=['Category', 'Amount'])
        
        if not exp_df.empty:
            exp_df['Amount'] = exp_df['Amount'].astype(float)
            exp_df = exp_df.sort_values(by='Amount', ascending=False).head(5)
            
            # Add %
            total_exp = curr_metrics['expenses']
            if total_exp > 0:
                exp_df['%'] = (exp_df['Amount'] / total_exp * 100).astype(float).round(1).astype(str) + '%'
            else:
                exp_df['%'] = '0.0%'
            
            exp_df['Amount'] = exp_df['Amount'].apply(format_currency)
            st.dataframe(exp_df, hide_index=True, use_container_width=True)
        else:
            st.info("No expenses found for this month.")

    # 6. HTML EMAIL GENERATION
    st.divider()
    st.header("📧 Email Report Generator")

    # Generate HTML
    month_name = selected_month.strftime('%B %Y')
    prev_month_name = prev_month.strftime('%B %Y')
    
    def get_diff_html(curr, prev):
       d = curr - prev
       pct = ((d/prev)*100) if prev!=0 else 0
       color = "#10b981" if d >= 0 else "#ef4444" # Green if up, Red if down
       sym = "+" if d >= 0 else ""
       return f"""
       <span style="font-weight:bold;">{format_currency(curr)}</span> 
       <span style="color: #64748b; font-size: 0.9em;">vs {format_currency(prev)}</span> 
       <span style="color: {color}; font-weight: bold; font-size: 0.9em;">[{sym}{d:,.0f} ({sym}{pct:.1f}%)]</span>
       """

    # --- HTML STYLES ---
    html_styles = """
    <style>
        body { font-family: Helvetica, Arial, sans-serif; color: #333; line-height: 1.4; background-color: #ffffff; }
        .container { max-width: 100%; margin: 0; padding: 20px; border: none; }
        .header { text-align: center; border-bottom: 3px solid #3b82f6; padding-bottom: 10px; margin-bottom: 20px; }
        .header h2 { color: #1e293b; margin: 0; font-size: 22px; text-transform: uppercase; letter-spacing: 0.5px; }
        
        /* Summary Grid - Converted to Table for Email Client Support */
        .summary-table { width: 100%; border-collapse: separate; border-spacing: 10px; margin-bottom: 25px; table-layout: fixed; }
        .summary-cell { width: 33.33%; padding: 0; vertical-align: top; }
        .summary-card { padding: 15px; border-radius: 8px; color: white; display: block; overflow: hidden; } /* block instead of flex */
        .summary-label { font-size: 11px; opacity: 0.95; margin-bottom: 8px; display: block; text-transform: uppercase; font-weight: 600; }
        .summary-val { font-size: 20px; font-weight: bold; display: block; margin-bottom: 8px; line-height: 1.1; white-space: nowrap; }
        .summary-sub { font-size: 10px; opacity: 0.95; line-height: 1.3; border-top: 1px solid rgba(255,255,255,0.3); padding-top: 6px; }
        
        /* Gradients */
        .card-green { background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%); background-color: #22c55e; }
        .card-red { background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); background-color: #ef4444; }
        .card-purple { background: linear-gradient(135deg, #a855f7 0%, #7e22ce 100%); background-color: #a855f7; }

        /* Corporate Data Tables */
        .section-title { 
            color: #1e293b; font-size: 14px; font-weight: bold; margin-top: 25px; margin-bottom: 10px; 
            border-left: 4px solid #3b82f6; padding-left: 10px; line-height: 1.2;
            display: flex; align-items: center;
        }
        .card-box { margin-bottom: 20px; background: #fff; }
        
        table.data-table { width: 100%; border-collapse: collapse; font-size: 13px; border: 1px solid #e2e8f0; }
        thead { background-color: #0ea5e9; color: white; }
        th { text-align: left; padding: 10px; font-weight: 600; font-size: 12px; text-transform: uppercase; }
        td { padding: 10px; border-bottom: 1px solid #e2e8f0; color: #334155; }
        tr:nth-child(even) { background-color: #f8fafc; }
        
        .total-row td { 
            font-weight: bold; 
            background-color: #f1f5f9; 
            color: #0f172a; 
            border-top: 2px solid #cbd5e1;
        }
        .align-right { text-align: right; }

        /* Net Balance */
        .net-title { 
            background-color: #f0f9ff; border: 1px solid #bae6fd; color: #0369a1; 
            padding: 10px 15px; border-radius: 6px; text-align: right; font-weight: bold;
            margin: 20px 0; font-size: 15px;
        }
        
        /* Horizontal Balances - Table */
        .balance-table { width: 100%; border-collapse: collapse; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; margin-top: 5px; }
        .bal-cell { text-align: center; border-right: 1px solid #e2e8f0; padding: 15px; vertical-align: top; }
        .bal-cell:last-child { border-right: none; }
        .bal-label { display: block; font-size: 10px; color: #64748b; font-weight: bold; text-transform: uppercase; margin-bottom: 4px; }
        .bal-value { display: block; font-size: 13px; font-weight: bold; color: #0f172a; white-space: nowrap; }

        .footer { font-size: 10px; color: #94a3b8; text-align: center; margin-top: 30px; border-top: 1px solid #e2e8f0; padding-top: 15px; }
    </style>
    """

    # --- HTML CONTENT ASSEMBLY ---
    
    def get_card_stats(curr, prev):
        if prev == 0:
            return "No prev data"
        d = curr - prev
        pct = (d / prev) * 100
        direction = "Up" if d >= 0 else "Down"
        # Arrow: ▲ or ▼
        arrow = "▲" if d >= 0 else "▼"
        return f"""
        Prev: {format_currency(prev)}<br>
        {arrow} {direction} by {abs(pct):.1f}%
        """

    # Wise Rows
    wise_rows = ""
    for k, v in curr_metrics['wise_breakdown'].items():
        wise_rows += f"<tr><td>{k}</td><td class='align-right'>{format_currency(v)}</td></tr>"
    
    # Income Rows
    inc_rows = ""
    sorted_inc = sorted(curr_metrics['income_breakdown'].items(), key=lambda x: x[1], reverse=True)
    for k, v in sorted_inc:
        pct = (v / curr_metrics['income'] * 100) if curr_metrics['income'] > 0 else 0
        inc_rows += f"<tr><td>{k}</td><td class='align-right'>{format_currency(v)} <span style='color:#94a3b8; font-size:0.8em;'>({pct:.1f}%)</span></td></tr>"

    # Expense Rows
    exp_rows = ""
    sorted_exp = sorted(curr_metrics['expense_breakdown'].items(), key=lambda x: x[1], reverse=True)
    for k, v in sorted_exp:
        pct = (v / curr_metrics['expenses'] * 100) if curr_metrics['expenses'] > 0 else 0
        exp_rows += f"<tr><td>{k}</td><td class='align-right'>{format_currency(v)} <span style='color:#94a3b8; font-size:0.8em;'>({pct:.1f}%)</span></td></tr>"

    # Balance Row HTML (Table Cells)
    bal_cells_html = ""
    num_bals = len(curr_balances) if len(curr_balances) > 0 else 1
    cell_width = f"{100/num_bals:.1f}%"
    
    for k, v in curr_balances.items():
        bal_cells_html += f"""
        <td class="bal-cell" width="{cell_width}">
            <span class="bal-label">{k}</span>
            <span class="bal-value">{format_currency(v)}</span>
        </td>
        """

    html_content = f"""
    <html>
    <head>{html_styles}</head>
    <body>
        <div class="container">
            <div class="header">
                <h2>Nepal Finance Overview</h2>
                <div style="color: #64748b;">{month_name}</div>
            </div>
            
            <p>Dear Sirs,</p>
            <p>Please find below the financial overview for <b>{month_name}</b>.</p>

            <div class="section-title">📊 Income Breakdown</div>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Source</th>
                        <th class="align-right">Amount</th>
                    </tr>
                </thead>
                <tbody>
                    {inc_rows}
                    <tr class="total-row"><td>TOTAL</td><td class="align-right">{format_currency(curr_metrics['income'])}</td></tr>
                </tbody>
            </table>

            <div class="section-title">🏦 Transfer from Wise</div>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Source</th>
                        <th class="align-right">Amount</th>
                    </tr>
                </thead>
                <tbody>
                    {wise_rows}
                    <tr class="total-row"><td>TOTAL</td><td class="align-right">{format_currency(curr_metrics['wise'])}</td></tr>
                </tbody>
            </table>

            <div class="section-title">💸 Expense Breakdown</div>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Category</th>
                        <th class="align-right">Amount</th>
                    </tr>
                </thead>
                <tbody>
                    {exp_rows}
                    <tr class="total-row"><td>TOTAL</td><td class="align-right">{format_currency(curr_metrics['expenses'])}</td></tr>
                </tbody>
            </table>
            
            <div class="net-title">
                Net Balance: {format_currency(curr_metrics['net_balance'])}
            </div>

            <!-- Summary Cards using Table for Email Compatibility -->
            <table class="summary-table" role="presentation" border="0" cellpadding="0" cellspacing="0">
                <tr>
                    <td class="summary-cell">
                        <div class="summary-card card-green">
                            <span class="summary-label">Income</span>
                            <span class="summary-val">{format_currency(curr_metrics['income'])}</span>
                            <div class="summary-sub">{get_card_stats(curr_metrics['income'], prev_metrics['income'])}</div>
                        </div>
                    </td>
                    <!-- Spacer -->
                    <td width="15"></td>
                    <td class="summary-cell">
                        <div class="summary-card card-red">
                            <span class="summary-label">Expenses</span>
                            <span class="summary-val">{format_currency(curr_metrics['expenses'])}</span>
                            <div class="summary-sub">{get_card_stats(curr_metrics['expenses'], prev_metrics['expenses'])}</div>
                        </div>
                    </td>
                    <!-- Spacer -->
                    <td width="15"></td>
                    <td class="summary-cell">
                        <div class="summary-card card-purple">
                            <span class="summary-label">Transfers</span>
                            <span class="summary-val">{format_currency(curr_metrics['wise'])}</span>
                            <div class="summary-sub">{get_card_stats(curr_metrics['wise'], prev_metrics['wise'])}</div>
                        </div>
                    </td>
                </tr>
            </table>

            <div class="section-title">💰 Ending Balances</div>
            <table class="balance-table">
                <tr>
                    {bal_cells_html}
                </tr>
            </table>

            <div class="footer">
                Automated Report | {datetime.now().strftime('%Y-%m-%d %H:%M')}
            </div>
        </div>
    </body>
    </html>
    """
    
    # --- EMAIL SIDEBAR CONFIG ---
    import json
    import os
    CONFIG_FILE = "config.json"

    def load_config():
        if os.path.exists(CONFIG_FILE):
             try:
                 with open(CONFIG_FILE, "r") as f: return json.load(f)
             except: return {}
        return {}

    def save_config(email, password, recipients):
        data = {"sender_email": email, "sender_password": password, "recipients": recipients}
        with open(CONFIG_FILE, "w") as f: json.dump(data, f)
    
    config = load_config()

    with st.sidebar:
        st.header("Email Configuration")
        sender_email = st.text_input("Sender Email", value=config.get("sender_email", ""))
        sender_password = st.text_input("App Password", value=config.get("sender_password", ""), type="password")
        st.info("Use an App Password if using Gmail.")
        if st.button("💾 Save Config"):
            save_config(sender_email, sender_password, config.get("recipients", "")) 
            st.success("Config Saved")

    col_preview, col_send = st.columns([3, 1])
    
    with col_preview:
        st.subheader("Preview")
        # Display HTML in a container
        st.components.v1.html(html_content, height=800, scrolling=True)
        
    with col_send:
        st.info("Configure sender details in the sidebar first.")
        
        # --- EXCOM QUICK FILL ---
        excom_list = "santosh@globalselect.com.au, Satish@globalselect.com.au, accounts@globalselect.com.au"
        if st.button("👥 Mail to Excoms", help="Auto-fill Executive Committee emails"):
             st.session_state['recipients_8'] = excom_list
        
        if 'recipients_8' not in st.session_state:
             st.session_state['recipients_8'] = config.get("recipients", "someone@example.com")

        recipients = st.text_input("Recipients", key="recipients_8")
        subject = st.text_input("Subject", f"Financial Report - {month_name}")
        
        if st.button("🚀 Send HTML Email", type="primary"):
            if not sender_email or not sender_password:
                st.error("Missing Sender Creds!")
            else:
                try:
                    msg = MIMEMultipart('alternative')
                    msg['From'] = sender_email
                    msg['To'] = recipients
                    msg['Subject'] = subject
                    
                    # Attach HTML version
                    msg.attach(MIMEText(html_content, 'html'))
                    
                    server = smtplib.SMTP('smtp.gmail.com', 587)
                    server.starttls()
                    server.login(sender_email, sender_password)
                    server.sendmail(sender_email, [r.strip() for r in recipients.split(',')], msg.as_string())
                    server.quit()
                    
                    save_config(sender_email, sender_password, recipients)
                    st.success("HTML Email Sent Successfully!")
                except Exception as e:
                    st.error(f"Error: {e}")

except Exception as e:
    st.error(f"Error loading or processing data: {e}")
    st.exception(e)
