import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io
import json
import os

# 1. PAGE SETUP
st.set_page_config(page_title="COE Report Automator", page_icon="🎓", layout="wide")
st.title("🎓 COE Report Automator")
st.write("Upload your COE data file to generate automated reports.")

# 2. FILE UPLOADER
uploaded_file = st.file_uploader("Upload Excel file", type=['xlsx', 'xls'])

if uploaded_file is not None:
    try:
        # Load the file
        df = pd.read_excel(uploaded_file, engine='openpyxl')
        st.success(f"✅ File uploaded successfully! Loaded {len(df)} records.")
        
        # Display column names for debugging
        with st.expander("📋 View Column Names"):
            st.write(f"Total columns: {len(df.columns)}")
            st.write(df.columns.tolist())
        
        # 3. PROCESSING LOGIC
        # Column mapping (0-indexed: A=0, O=14, S=18, L=11, AU=46, AO=40)
        try:
            # Convert column O (Date COE received) to datetime
            date_coe_col = df.columns[14]  # Column O (0-indexed)
            df[date_coe_col] = pd.to_datetime(df[date_coe_col], errors='coerce')
            
            # Convert column S (Course End date / COE end date) to datetime
            coe_end_col = df.columns[18]  # Column S
            df[coe_end_col] = pd.to_datetime(df[coe_end_col], errors='coerce')
            
            st.divider()
            
            # ============================================
            # REPORT 1: COE EXPIRY ANALYSIS
            # ============================================
            st.header("📊 Report 1: COE Expiry Analysis")
            
            # Calculate date thresholds
            today = datetime.now()
            eighteen_months_ago = today - timedelta(days=18*30)  # Approx 18 months
            six_months_future = today + timedelta(days=6*30)  # Approx 6 months
            
            # Sheet 1: COE received in past 18 months
            mask_18_months = (df[date_coe_col] >= eighteen_months_ago) & (df[date_coe_col] <= today)
            df_18_months = df[mask_18_months].copy()
            
            # Sheet 2: COE expiry < 6 months
            mask_expiring = (df[coe_end_col] >= today) & (df[coe_end_col] <= six_months_future)
            df_expiring = df[mask_expiring].copy()
            
            # Select columns A to W (0-indexed: 0 to 22)
            cols_a_to_w = df.columns[0:23].tolist()
            df_18_months_filtered = df_18_months[cols_a_to_w]
            df_expiring_filtered = df_expiring[cols_a_to_w]
            
            # Display metrics
            col1, col2 = st.columns(2)
            col1.metric("COE Received (Past 18 Months)", len(df_18_months_filtered))
            col2.metric("COE Expiring (< 6 Months)", len(df_expiring_filtered))
            
            # Display data
            tab1, tab2 = st.tabs(["COE Received (18M)", "COE Expiring (6M)"])
            
            with tab1:
                st.subheader("COE Received in Past 18 Months")
                if not df_18_months_filtered.empty:
                    st.dataframe(df_18_months_filtered, use_container_width=True)
                else:
                    st.info("No records found.")
            
            with tab2:
                st.subheader("COE Expiring < 6 Months")
                if not df_expiring_filtered.empty:
                    st.dataframe(df_expiring_filtered, use_container_width=True)
                else:
                    st.info("No records found.")
            
            # Download button for Report 1
            buffer1 = io.BytesIO()
            with pd.ExcelWriter(buffer1, engine='xlsxwriter') as writer:
                df_18_months_filtered.to_excel(writer, sheet_name='COE Received 18M', index=False)
                df_expiring_filtered.to_excel(writer, sheet_name='COE Expiring 6M', index=False)
            
            st.download_button(
                label="📥 Download COE Expiry Report",
                data=buffer1,
                file_name=f"COE_Expiry_Report_{datetime.now().date()}.xlsx",
                mime="application/vnd.ms-excel"
            )
            
            # Email section for Report 1
            st.subheader("📧 Email COE Expiry Report")
            
            CONFIG_FILE = "config.json"
            
            def load_config():
                if os.path.exists(CONFIG_FILE):
                    try:
                        with open(CONFIG_FILE, "r") as f:
                            return json.load(f)
                    except:
                        return {}
                return {}
            
            config = load_config()
            
            with st.sidebar:
                st.header("Email Configuration")
                default_email = config.get("sender_email", "")
                default_password = config.get("sender_password", "")
                
                sender_email = st.text_input("Sender Email", value=default_email, key="coe_sender")
                sender_password = st.text_input("App Password", value=default_password, type="password", key="coe_pass")
                st.info("Shared with all reports")
            
            default_recipients_expiry = config.get("coe_expiry_recipients", "")
            recipients_expiry = st.text_input("Recipients (comma separated)", value=default_recipients_expiry, key="coe_expiry_recipients", help="Email recipients for COE Expiry Report")
            
            email_subject_expiry = st.text_input("Subject", f"COE Expiry Report - {datetime.now().date()}", key="subject_expiry")
            
            default_body_expiry = f"""Hi Team,

Please find attached the COE Expiry Report for {datetime.now().date()}.

Summary:
- COE Received (Past 18 Months): {len(df_18_months_filtered)}
- COE Expiring (< 6 Months): {len(df_expiring_filtered)}

Regards,
Ashish Shrestha"""

            email_body_expiry = st.text_area("Email Draft", default_body_expiry, height=200, key="body_expiry")

            if st.button("🚀 Send COE Expiry Report", key="send_expiry"):
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
                        msg['To'] = recipients_expiry
                        msg['Subject'] = email_subject_expiry

                        msg.attach(MIMEText(email_body_expiry, 'plain'))

                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(buffer1.getvalue())
                        encoders.encode_base64(part)
                        part.add_header('Content-Disposition', f"attachment; filename=COE_Expiry_Report_{datetime.now().date()}.xlsx")
                        msg.attach(part)

                        server = smtplib.SMTP('smtp.gmail.com', 587)
                        server.starttls()
                        server.login(sender_email, sender_password)
                        
                        recipient_list = [r.strip() for r in recipients_expiry.split(',')]
                        server.sendmail(sender_email, recipient_list, msg.as_string())
                        server.quit()

                        st.success(f"Email sent successfully to: {recipients_expiry}!")
                    except Exception as e:
                        st.error(f"Failed to send email. Error: {e}")
            
            st.divider()
            
            # ============================================
            # REPORT 2: CURRENT MONTH COE SALES
            # ============================================
            st.header("📈 Report 2: Current Month COE Sales")
            
            # Month selector
            st.subheader("Select Month")
            col1, col2 = st.columns(2)
            
            # Get unique months from data
            df['year_month'] = df[date_coe_col].dt.to_period('M')
            available_months = sorted(df['year_month'].dropna().unique(), reverse=True)
            
            if available_months:
                # Convert to datetime for display
                month_options = [pd.Period(m).to_timestamp() for m in available_months]
                month_labels = [m.strftime('%B %Y') for m in month_options]
                
                with col1:
                    selected_month_label = st.selectbox(
                        "Choose Month",
                        options=month_labels,
                        index=0,  # Default to latest month
                        key="month_selector"
                    )
                
                # Get the selected month's start and end dates
                selected_month_idx = month_labels.index(selected_month_label)
                selected_month_date = month_options[selected_month_idx]
                selected_month_start = pd.Timestamp(selected_month_date.year, selected_month_date.month, 1)
                selected_month_end = (selected_month_start + pd.DateOffset(months=1)) - pd.DateOffset(days=1)
                
                with col2:
                    st.info(f"**Period:** {selected_month_start.strftime('%b %d')} - {selected_month_end.strftime('%b %d, %Y')}")
                
                # Filter for selected month using column O (Date COE received)
                mask_selected_month = (df[date_coe_col] >= selected_month_start) & (df[date_coe_col] <= selected_month_end)
                df_current_month = df[mask_selected_month].copy()
            
            if not df_current_month.empty:
                # Column references
                consultant_col = df.columns[46]  # Column AU
                coe_type_col = df.columns[11]   # Column L
                net_sales_col = df.columns[40]  # Column AO
                
                # Clean data
                df_current_month[consultant_col] = df_current_month[consultant_col].fillna('Unknown')
                df_current_month[coe_type_col] = df_current_month[coe_type_col].fillna('Unknown')
                df_current_month[net_sales_col] = pd.to_numeric(df_current_month[net_sales_col], errors='coerce').fillna(0)
                
                # Create pivot table
                # Group by Consultant and COE Type
                summary = df_current_month.groupby([consultant_col, coe_type_col]).agg({
                    date_coe_col: 'count',  # Count of COE
                    net_sales_col: 'sum'    # Sum of sales
                }).reset_index()
                
                summary.columns = ['Sales Team', 'COE Type', 'No of CoE', 'Gross Sales']
                
                # Pivot to create the table format
                pivot = summary.pivot(index='Sales Team', columns='COE Type', values=['No of CoE', 'Gross Sales'])
                
                # Calculate totals
                totals = df_current_month.groupby(consultant_col).agg({
                    date_coe_col: 'count',
                    net_sales_col: 'sum'
                }).reset_index()
                totals.columns = ['Sales Team', 'Total No of CoE', 'Total Gross Sales']
                
                # Merge with pivot
                final_table = totals.copy()
                
                # Add columns for each COE type
                coe_types = summary['COE Type'].unique()
                for coe_type in sorted(coe_types):
                    type_data = summary[summary['COE Type'] == coe_type][['Sales Team', 'No of CoE', 'Gross Sales']]
                    type_data.columns = ['Sales Team', f'{coe_type}_No', f'{coe_type}_Sales']
                    final_table = final_table.merge(type_data, on='Sales Team', how='left')
                
                # Fill NaN with 0
                final_table = final_table.fillna(0)
                
                # Add grand totals row
                totals_row = {'Sales Team': 'Grand Total'}
                totals_row['Total No of CoE'] = final_table['Total No of CoE'].sum()
                totals_row['Total Gross Sales'] = final_table['Total Gross Sales'].sum()
                for coe_type in sorted(coe_types):
                    if f'{coe_type}_No' in final_table.columns:
                        totals_row[f'{coe_type}_No'] = final_table[f'{coe_type}_No'].sum()
                    if f'{coe_type}_Sales' in final_table.columns:
                        totals_row[f'{coe_type}_Sales'] = final_table[f'{coe_type}_Sales'].sum()
                
                # Append totals row
                final_table = pd.concat([final_table, pd.DataFrame([totals_row])], ignore_index=True)
                
                # Format for display
                display_table = final_table.copy()
                
                # Display the table
                st.subheader("📊 Sales Summary by Consultant")
                st.dataframe(display_table, use_container_width=True)
                
                # Create targets table
                st.subheader("🎯 Monthly Targets & Shortfall")
                
                TARGET_COE = 7  # Target COE per salesperson
                
                # Get consultant totals (excluding Grand Total row)
                consultant_data = final_table[final_table['Sales Team'] != 'Grand Total'].copy()
                
                targets_table = pd.DataFrame({
                    'Sales Team': consultant_data['Sales Team'],
                    'Total COE': consultant_data['Total No of CoE'].astype(int),
                    'Target': TARGET_COE,
                    'Shortfall': (TARGET_COE - consultant_data['Total No of CoE']).astype(int)
                })
                
                # Add COE type specific columns
                for coe_type in sorted(coe_types):
                    if f'{coe_type}_No' in consultant_data.columns:
                        targets_table[f'{coe_type}'] = consultant_data[f'{coe_type}_No'].astype(int)
                
                # Add grand total for targets table
                targets_total_row = {
                    'Sales Team': 'Grand Total',
                    'Total COE': int(targets_table['Total COE'].sum()),
                    'Target': TARGET_COE * len(consultant_data),
                    'Shortfall': int(targets_table['Shortfall'].sum())
                }
                for coe_type in sorted(coe_types):
                    if coe_type in targets_table.columns:
                        targets_total_row[coe_type] = int(targets_table[coe_type].sum())
                
                targets_table = pd.concat([targets_table, pd.DataFrame([targets_total_row])], ignore_index=True)
                
                # Display targets table
                st.dataframe(targets_table, use_container_width=True)
                
                
                # Download button for Report 2
                buffer2 = io.BytesIO()
                with pd.ExcelWriter(buffer2, engine='xlsxwriter') as writer:
                    display_table.to_excel(writer, sheet_name='Current Month Sales', index=False)
                    df_current_month.to_excel(writer, sheet_name='Raw Data', index=False)
                
                st.download_button(
                    label="📥 Download Current Month Sales Report",
                    data=buffer2,
                    file_name=f"COE_Sales_{selected_month_date.strftime('%B_%Y')}.xlsx",
                    mime="application/vnd.ms-excel"
                )
                
                # Email section for Report 2
                st.subheader("📧 Email Current Month Sales Report")
                
                default_recipients_sales = config.get("coe_sales_recipients", "")
                recipients_sales = st.text_input("Recipients (comma separated)", value=default_recipients_sales, key="coe_sales_recipients", help="Email recipients for Current Month Sales Report")
                
                # Email subject - use unique key per month to force reactivity
                subject_key = f"subject_sales_{selected_month_date.strftime('%Y_%m')}"
                default_subject = f"COE Sales Report - {selected_month_date.strftime('%B %Y')}"
                email_subject_sales = st.text_input("Subject", value=default_subject, key=subject_key)
                
                # Convert table to HTML
                table_html = display_table.to_html(index=False, border=1, classes='dataframe')
                
                # Style the HTML table
                styled_table_html = table_html.replace('<table border="1" class="dataframe">', 
                    '<table style="border-collapse:collapse; width:100%; font-family:Arial,sans-serif; font-size:13px;">')
                styled_table_html = styled_table_html.replace('<th>', '<th style="background-color:#3498db; color:white; padding:8px; text-align:left; border:1px solid #ddd;">')
                styled_table_html = styled_table_html.replace('<td>', '<td style="border:1px solid #ddd; padding:6px;">')
                styled_table_html = styled_table_html.replace('<tr>', '<tr style="background-color:#f9f9f9;">')
                
                html_body_sales = f"""<html>
<head>
<style>
body {{font-family: Arial, sans-serif; font-size: 14px; line-height: 1.6; color: #333;}}
h2 {{color: #2c3e50; font-size: 16px; margin-top: 20px;}}
table {{border-collapse: collapse; width: 100%; margin: 15px 0;}}
th {{background-color: #3498db; color: white; padding: 8px; text-align: left; border: 1px solid #ddd;}}
td {{border: 1px solid #ddd; padding: 6px;}}
tr:nth-child(even) {{background-color: #f9f9f9;}}
</style>
</head>
<body>
<p>Hi Team,</p>
<p>Please find attached the COE Sales Report for <strong>{selected_month_date.strftime('%B %Y')}</strong>.</p>
<p>This report covers COE sales from <strong>{selected_month_start.strftime('%B %d')}</strong> to <strong>{selected_month_end.strftime('%B %d, %Y')}</strong>.</p>

<h2>📊 Sales Summary</h2>
{styled_table_html}

<h2>📈 Overall Summary</h2>
<ul>
<li><strong>Total COE Count:</strong> {len(df_current_month)}</li>
<li><strong>Total Sales:</strong> NPR {df_current_month[net_sales_col].sum():,.0f}</li>
</ul>

<p>Please find the detailed Excel report attached.</p>

<p>Best regards,<br>
<strong>Ashish Shrestha</strong></p>
</body>
</html>"""

                # Show preview
                with st.expander("📧 Email Preview", expanded=False):
                    st.components.v1.html(html_body_sales, height=600, scrolling=True)

                if st.button("🚀 Send Current Month Sales Report", key="send_sales"):
                    if not sender_email or not sender_password:
                        st.error("Please configure email settings in the sidebar")
                    else:
                        try:
                            import smtplib
                            from email.mime.multipart import MIMEMultipart
                            from email.mime.text import MIMEText
                            from email.mime.base import MIMEBase
                            from email import encoders

                            msg = MIMEMultipart('alternative')
                            msg['From'] = sender_email
                            msg['To'] = recipients_sales
                            msg['Subject'] = email_subject_sales

                            msg.attach(MIMEText(html_body_sales, 'html'))

                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(buffer2.getvalue())
                            encoders.encode_base64(part)
                            part.add_header('Content-Disposition', f"attachment; filename=COE_Sales_{selected_month_date.strftime('%B_%Y')}.xlsx")
                            msg.attach(part)

                            server = smtplib.SMTP('smtp.gmail.com', 587)
                            server.starttls()
                            server.login(sender_email, sender_password)
                            
                            recipient_list = [r.strip() for r in recipients_sales.split(',')]
                            server.sendmail(sender_email, recipient_list, msg.as_string())
                            server.quit()

                            st.success(f"Email sent successfully to: {recipients_sales}!")
                        except Exception as e:
                            st.error(f"Failed to send email. Error: {e}")
                
                
            else:
                st.warning("No COE records found for current month.")
            
        except Exception as e:
            st.error(f"Error processing data: {e}")
            st.write("**Debug Info:**")
            st.write(f"Total columns: {len(df.columns)}")
            st.write("Please verify column positions:")
            st.write("- Column O (index 14): Date COE received")
            st.write("- Column S (index 18): Course End date")
            st.write("- Column L (index 11): COE Type")
            st.write("- Column AU (index 46): Consultant")
            st.write("- Column AO (index 40): Net sales")
            
    except Exception as e:
        st.error(f"Error loading file: {e}")
        st.write("Please ensure you're uploading a valid Excel file.")
