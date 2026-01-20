import streamlit as st
import pandas as pd
from datetime import datetime
import io
import json
import os
import matplotlib.pyplot as plt
import base64
from io import BytesIO

# Page configuration
st.set_page_config(page_title="IELTS/PTE Report", page_icon="📚", layout="wide")
st.title("📚 IELTS/PTE Report Automator")
st.write("Automated intelligent reporting with payment tracking and analytics")

# Configuration
CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

# Data URLs
PAYMENT_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQxrqK_lupLKcWGYwHU2MWnnJw3xWZc_V8DDtuTELd3oF3CEjbQlF4KLsNfSvv3IbDvx8mIFHVl3bIW/pub?gid=904067204&single=true&output=csv"
ENROLLMENT_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQxrqK_lupLKcWGYwHU2MWnnJw3xWZc_V8DDtuTELd3oF3CEjbQlF4KLsNfSvv3IbDvx8mIFHVl3bIW/pub?gid=0&single=true&output=csv"
EXPENSES_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQxrqK_lupLKcWGYwHU2MWnnJw3xWZc_V8DDtuTELd3oF3CEjbQlF4KLsNfSvv3IbDvx8mIFHVl3bIW/pub?gid=1621737816&single=true&output=csv"

# Load data automatically
with st.spinner("Fetching data from Google Sheets..."):
    try:
        # Fetch payment data
        df_payments = pd.read_csv(PAYMENT_URL)
        df_payments.columns = df_payments.columns.str.strip()
        
        # Fetch enrollment data
        df_enrollments = pd.read_csv(ENROLLMENT_URL)
        df_enrollments.columns = df_enrollments.columns.str.strip()
        
        # Fetch expenses data (teacher payments)
        df_expenses = pd.read_csv(EXPENSES_URL)
        df_expenses.columns = df_expenses.columns.str.strip()
        df_expenses['Month'] = pd.to_datetime(df_expenses['Month'], errors='coerce')
        df_expenses['MonthYear'] = df_expenses['Month'].dt.to_period('M').astype(str)  # Convert to string immediately
        
        st.success(f"✅ Loaded {len(df_payments)} payments, {len(df_enrollments)} enrollments, {len(df_expenses)} expense records")
        
        # Show data preview
        with st.expander("📊 Preview Raw Data"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.subheader("Payment Transactions")
                st.dataframe(df_payments.head(5), use_container_width=True)
            with col2:
                st.subheader("Student Enrollment")
                st.dataframe(df_enrollments.head(5), use_container_width=True)
            with col3:
                st.subheader("Teacher Expenses")
                st.dataframe(df_expenses.head(5), use_container_width=True)
            with col2:
                st.subheader("Student Enrollments")
                st.dataframe(df_enrollments, use_container_width=True)
        
        st.divider()
        
        # Clean and normalize data
        df_payments['Date'] = pd.to_datetime(df_payments['Date'], errors='coerce')
        df_payments['Students Name'] = df_payments['Students Name'].str.strip().str.lower()
        df_payments['Course Type'] = df_payments['Course Type'].str.strip()
        df_enrollments['Name'] = df_enrollments['Name'].str.strip().str.lower()
        
        # Add month/year column for filtering
        df_payments['MonthYear'] = df_payments['Date'].dt.to_period('M').astype(str)
        df_expenses['MonthYear'] = df_expenses['MonthYear'].astype(str)
        
        # Date Range Selector (Month-Wise)
        st.header("📅 Select Month Range")
        
        # Get all available months from data
        unique_months = sorted(list(set(df_payments['MonthYear'].dropna().unique())), reverse=True)
        if not unique_months:
            unique_months = [pd.Timestamp.now().strftime('%Y-%m')]
        
        col1, col2 = st.columns(2)
        with col1:
            # Default to oldest month
            start_month_str = st.selectbox("From Month", options=unique_months, index=len(unique_months)-1)
        with col2:
            # Default to newest month
            end_month_str = st.selectbox("To Month", options=unique_months, index=0)
            
        # Convert selected months to date range
        # Start date = 1st day of start month
        start_date = pd.Period(start_month_str).start_time.date()
        # End date = Last day of end month
        end_date = pd.Period(end_month_str).end_time.date()
        
        # Handle case if user selects From > To
        if start_date > end_date:
            st.error("⚠️ Start month cannot be after End month. Please adjust selection.")
            # Fallback to single month logic to prevent crash
            temp = start_date
            start_date = pd.Period(end_month_str).start_time.date()
            end_date = pd.Period(start_month_str).end_time.date()
        
        # Filter data based on date range
        df_payments_filtered = df_payments[
            (df_payments['Date'].dt.date >= start_date) & 
            (df_payments['Date'].dt.date <= end_date)
        ].copy()
        
        df_expenses_filtered = df_expenses[
            (df_expenses['Month'].dt.date >= start_date) & 
            (df_expenses['Month'].dt.date <= end_date)
        ].copy()
        
        st.info(f"Showing data from **{start_date.strftime('%B %d, %Y')}** to **{end_date.strftime('%B %d, %Y')}**")
        
        st.info(f"Showing data from **{start_date.strftime('%B %d, %Y')}** to **{end_date.strftime('%B %d, %Y')}**")
        
        st.divider()
        
        # Calculate total paid per student from filtered data
        payment_summary = df_payments_filtered.groupby('Students Name').agg({
            'Paid Amount': 'sum'
        }).reset_index()
        payment_summary.columns = ['name', 'total_paid']
        
        # Merge with enrollment data
        df_enrollments['name_lower'] = df_enrollments['Name']
        df_analysis = df_enrollments.merge(
            payment_summary, 
            left_on='name_lower', 
            right_on='name', 
            how='left'
        )
        
        # Fill NaN with 0 for students who haven't paid
        df_analysis['total_paid'] = df_analysis['total_paid'].fillna(0)
        
        # Calculate balance - handle missing Payment column
        # Ensure Payment column exists, default to 0 if not present
        if 'Payment' not in df_analysis.columns:
            df_analysis['Payment'] = 0
        
        # Fill NaN in Payment column
        df_analysis['Payment'] = df_analysis['Payment'].fillna(0)
        
        # Calculate balance
        df_analysis['balance'] = df_analysis['Payment'] - df_analysis['total_paid']
        
        # Categorize students
        def categorize_student(row):
            note = str(row['Note']).lower() if pd.notna(row['Note']) else ''
            balance = row.get('balance', 0)  # Safe get with default
            total_paid = row.get('total_paid', 0)  # Safe get with default
            
            if 'ref' in note or 'reference' in note:
                return '🎁 Reference'
            elif 'dropped' in note:
                return '📉 Dropped'
            elif balance <= 0:
                return '✅ Fully Paid'
            elif total_paid > 0:
                return '⚠️ Partial Payment'
            else:
                return '❌ Outstanding'
        
        df_analysis['status'] = df_analysis.apply(categorize_student, axis=1)
        
        # CRITICAL: Use ENROLLMENT data as source of truth for students
        # Everyone in the enrollment sheet IS a student (IELTS/PTE)
        # Book-only purchases are NOT in the enrollment sheet
        df_students = df_analysis.copy()
        
        # Ensure balance column exists in df_students
        if 'balance' not in df_students.columns:
            df_students['balance'] = 0
        
        # For office breakdown and reporting, we'll use df_students (all enrolled students)
        # Some students might have 0 payment (references) but they're still students
        
        # Book revenue: ONLY standalone "Book" purchases (not IELTS+Book, not PTE+Book)
        # This prevents double counting since IELTS+Book revenue is already in student revenue
        df_books_payments = df_payments_filtered[
            (df_payments_filtered['Course Type'].str.strip().str.upper() == 'BOOK')
        ]
        
        # Display analytics
        st.header("📈 Analytics Dashboard")
        st.caption(f"Period: {start_date.strftime('%b %d, %Y')} to {end_date.strftime('%b %d, %Y')}")
        
        # Calculate expenses
        total_expenses = df_expenses_filtered['Amount'].sum()
        
        # Calculate new students added in the selected period (using enrollment Month column)
        df_enrollments['Month'] = pd.to_datetime(df_enrollments['Month'], errors='coerce')
        new_students_in_period = df_enrollments[
            (df_enrollments['Month'].dt.date >= start_date) & 
            (df_enrollments['Month'].dt.date <= end_date)
        ]
        new_students_count = len(new_students_in_period)
        
        # Metrics - Calculate outstanding EXCLUDING dropped students
        col1, col2, col3, col4 = st.columns(4)
        
        # Student revenue: All IELTS/PTE payments (including IELTS+Book, PTE+Book)
        total_student_revenue = df_payments_filtered[
            df_payments_filtered['Course Type'].str.contains('IELTS|PTE', case=False, na=False, regex=True)
        ]['Paid Amount'].sum()
        
        # Book revenue: ONLY standalone Book purchases
        total_book_revenue = df_books_payments['Paid Amount'].sum()
        
        # Total revenue should match payment sheet
        total_revenue = df_payments_filtered['Paid Amount'].sum()
        total_students = len(df_students)
        
        # FIXED: Outstanding balance excludes dropped students
        # Only count students who are:
        # 1. NOT dropped (from Note field)
        # 2. NOT references (from Note field)
        # 3. Have balance > 0
        active_students_with_balance = df_students[
            (~df_students['status'].isin(['📉 Dropped', '🎁 Reference'])) & 
            (df_students['balance'] > 0)
        ]
        total_outstanding = active_students_with_balance['balance'].sum()
        
        # Calculate profit/loss
        total_profit = total_revenue - total_expenses
        profit_emoji = "✅" if total_profit > 0 else "⚠️" if total_profit < 0 else "➖"
        profit_delta = f"{total_profit:,.0f}"
        
        col1.metric("💰 Total Revenue", f"NPR {total_revenue:,.0f}")
        col2.metric("💸 Total Expenses", f"NPR {total_expenses:,.0f}")
        col3.metric(f"{profit_emoji} Profit/Loss", f"NPR {total_profit:,.0f}", 
                   delta=None if total_profit == 0 else ("Profit" if total_profit > 0 else "Loss"))
        col4.metric("🆕 New Students", f"{new_students_count}")
        
        st.divider()
        
        # Secondary metrics
        col5, col6, col7, col8 = st.columns(4)
        col5.metric("👥 IELTS/PTE Students", f"{total_students}")
        col6.metric("🎓 Student Revenue", f"NPR {total_student_revenue:,.0f}")
        col7.metric("📚 Book Only Revenue", f"NPR {total_book_revenue:,.0f}")
        col8.metric("⚠️ Outstanding", f"NPR {total_outstanding:,.0f}")
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Student Status Breakdown")
            if not df_students.empty:
                status_counts = df_students['status'].value_counts()
                fig1, ax1 = plt.subplots(figsize=(8, 6))
                ax1.pie(status_counts.values, labels=status_counts.index, autopct='%1.1f%%', startangle=90)
                ax1.axis('equal')
                st.pyplot(fig1)
            else:
                st.info("No student data for selected period")
        
        with col2:
            st.subheader("Revenue Breakdown")
            revenue_data = pd.DataFrame({
                'Category': ['IELTS/PTE Students', 'Books'],
                'Revenue': [total_student_revenue, total_book_revenue]
            })
            fig2, ax2 = plt.subplots(figsize=(8, 6))
            revenue_data.plot(kind='bar', x='Category', y='Revenue', ax=ax2, color=['#3498db', '#e74c3c'], legend=False)
            ax2.set_ylabel('Revenue (NPR)')
            ax2.set_xlabel('')
            plt.xticks(rotation=0)
            st.pyplot(fig2)
        
        st.divider()
        
        # Detailed Tables
        st.header("📋 Detailed Reports")
        
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["Outstanding Payments", "Fully Paid", "Book Sales", "All Students", "Revenue Summary"])
        
        with tab1:
            st.subheader("Students with Outstanding Payments")
            st.caption("Shows ALL students with unpaid balance (excludes Dropped/Reference) - NOT filtered by selected time period")
            
            try:
                # CRITICAL: Outstanding is CURRENT STATE, not time-filtered
                # Use df_students (which is based on ENROLLMENT, not filtered by payment month)
                # Outstanding = students who have balance > 0, regardless of when they enrolled or paid
                
                # Debug: Check if balance column exists
                if 'balance' not in df_students.columns:
                    st.error("Balance column missing! Creating it now...")
                    df_students['balance'] = df_students.get('Payment', 0) - df_students.get('total_paid', 0)
                
                # Show ALL students with outstanding balance (NOT filtered by month)
                outstanding = df_students[
                    (~df_students['status'].isin(['📉 Dropped', '🎁 Reference'])) &
                    (df_students['balance'].fillna(0) > 0)
                ].copy()
                
                if not outstanding.empty:
                    # Ensure all required columns exist
                    required_cols = ['Name', 'Office', 'Month', 'Payment', 'total_paid', 'balance', 'status', 'Note']
                    for col in required_cols:
                        if col not in outstanding.columns:
                            outstanding[col] = 'N/A' if col in ['Name', 'Office', 'Month', 'status', 'Note'] else 0
                    
                    outstanding_display = outstanding[required_cols]
                    outstanding_display.columns = ['Name', 'Office', 'Enrolled Month', 'Expected', 'Paid', 'Balance', 'Status', 'Note']
                    st.dataframe(outstanding_display.sort_values('Balance', ascending=False), use_container_width=True)
                    
                    st.info(f"""
                    **Outstanding Summary:**
                    - Total students with balance: {len(outstanding)} students
                    - Total outstanding amount: NPR {outstanding['balance'].sum():,.0f}
                    - Note: This shows CURRENT outstanding balances, not filtered by selected time period
                    """)
                else:
                    st.success("✅ No outstanding payments!")
            
            except Exception as e:
                st.error(f"Error displaying outstanding payments: {str(e)}")
                st.info("Debug Info:")
                st.write(f"Columns in df_students: {', '.join(df_students.columns.tolist())}")
                st.write(f"Total students: {len(df_students)}")
                if len(df_students) > 0:
                    st.write("Sample student data:")
                    st.write(df_students.head(3))
        
        with tab2:
            st.subheader("Fully Paid Students")
            fully_paid = df_students[df_students['status'] == '✅ Fully Paid'].copy()
            if not fully_paid.empty:
                fully_paid_display = fully_paid[['Name', 'Office', 'Month', 'Payment', 'total_paid']]
                fully_paid_display.columns = ['Name', 'Office', 'Month', 'Expected', 'Paid']
                st.dataframe(fully_paid_display, use_container_width=True)
            else:
                st.info("No fully paid students for this period")
        
        with tab3:
            st.subheader("Standalone Book Sales")
            st.caption("Only includes standalone 'Book' purchases (not IELTS+Book or PTE+Book)")
            st.metric("Total Book Revenue", f"NPR {total_book_revenue:,.0f}")
            if not df_books_payments.empty:
                # Select available columns
                book_cols = ['Date', 'Students Name', 'Course Type', 'Paid Amount', 'Office']
                if 'Received From' in df_books_payments.columns:
                    book_cols.append('Received From')
                
                book_display = df_books_payments[book_cols].copy()
                
                # Rename columns
                col_names = ['Date', 'Customer', 'Book Type', 'Amount', 'Office']
                if 'Received From' in df_books_payments.columns:
                    col_names.append('Received By')
                book_display.columns = col_names
                
                st.dataframe(book_display, use_container_width=True)
            else:
                st.info("No standalone book sales for this period")
        
        with tab4:
            st.subheader("All IELTS/PTE Students")
            if not df_students.empty:
                all_students = df_students[['Name', 'Office', 'Month', 'Payment', 'total_paid', 'balance', 'status', 'Note']].copy()
                all_students.columns = ['Name', 'Office', 'Month', 'Expected', 'Paid', 'Balance', 'Status', 'Note']
                st.dataframe(all_students, use_container_width=True)
            else:
                st.info("No students for this period")
        
        with tab5:
            st.subheader("Revenue Summary")
            
            # Monthly revenue
            st.write("**Revenue by Month**")
            monthly_revenue = df_payments.groupby('MonthYear').agg({
                'Paid Amount': 'sum'
            }).reset_index()
            monthly_revenue.columns = ['Month', 'Revenue']
            monthly_revenue = monthly_revenue.sort_values('Month', ascending=False)
            st.dataframe(monthly_revenue, use_container_width=True)
            
            # Office revenue for selected period
            st.write(f"**Revenue & Students by Office ({start_date.strftime('%b %Y')} - {end_date.strftime('%b %Y')})**")
            
            # Get actual students by office from enrollment data
            office_breakdown = df_students.groupby('Office').agg({
                'Name': 'count',
                'status': lambda x: (x == '✅ Fully Paid').sum(),
            }).reset_index()
            office_breakdown.columns = ['Office', 'Total Students', 'Fully Paid']
            
            # Add revenue from payment data
            office_revenue_map = df_payments_filtered.groupby('Office')['Paid Amount'].sum().to_dict()
            office_breakdown['Revenue'] = office_breakdown['Office'].map(office_revenue_map).fillna(0)
            
            # Add outstanding, references, dropped counts
            for office in office_breakdown['Office']:
                office_students = df_students[df_students['Office'] == office]
                # FIXED: Outstanding excludes dropped and references - count number of students
                outstanding_count = len(
                    office_students[
                        (~office_students['status'].isin(['📉 Dropped', '🎁 Reference'])) &
                        (office_students['balance'] > 0)
                    ]
                )
                office_breakdown.loc[office_breakdown['Office'] == office, 'Outstanding'] = outstanding_count
                office_breakdown.loc[office_breakdown['Office'] == office, 'References'] = (office_students['status'] == '🎁 Reference').sum()
                office_breakdown.loc[office_breakdown['Office'] == office, 'Dropped'] = (office_students['status'] == '📉 Dropped').sum()
            
            # Reorder columns
            office_breakdown = office_breakdown[['Office', 'Total Students', 'Fully Paid', 'Outstanding', 'References', 'Dropped', 'Revenue']]
            office_breakdown['Revenue'] = office_breakdown['Revenue'].astype(int)
            st.dataframe(office_breakdown, use_container_width=True)
            
            # Smart Insights Section
            st.write("**💡 Smart Insights**")
            
            # Calculate insights
            total_enrolled = len(df_students)
            total_references = len(df_students[df_students['status'] == '🎁 Reference'])
            total_dropped = len(df_students[df_students['status'] == '📉 Dropped'])
            paying_students = total_enrolled - total_references
            
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"""
                **Student Breakdown:**
                - Total Enrolled: {total_enrolled} students
                - Paying Students: {paying_students} students
                - References (Free): {total_references} students
                - Dropped Out: {total_dropped} students
                """)
            
            with col2:
                # Payment completion rate
                fully_paid_count = len(df_students[df_students['status'] == '✅ Fully Paid'])
                if paying_students > 0:
                    completion_rate = (fully_paid_count / paying_students) * 100
                    st.success(f"""
                    **Payment Status:**
                    - Fully Paid: {fully_paid_count} students ({completion_rate:.1f}%)
                    - Pending: {paying_students - fully_paid_count} students
                    - Collection Rate: {completion_rate:.1f}%
                    """)

        
        st.divider()
        
        # Generate Excel Report
        st.header("📥 Download & Email Report")
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            # Sheet 1: Summary
            summary_data = {
                'Metric': ['Total Revenue', 'Student Revenue', 'Book Revenue', 'Outstanding Balance', 'Total Students'],
                'Value': [total_revenue, total_student_revenue, total_book_revenue, total_outstanding, total_students]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
            
            # Sheet 2: Outstanding
            if not outstanding.empty:
                outstanding_display.to_excel(writer, sheet_name='Outstanding Payments', index=False)
            
            # Sheet 3: Fully Paid
            if not fully_paid.empty:
                fully_paid_display.to_excel(writer, sheet_name='Fully Paid', index=False)
            
            # Sheet 4: All Students
            if not df_students.empty:
                all_students.to_excel(writer, sheet_name='All Students', index=False)
            
            # Sheet 5: Revenue Summary
            monthly_revenue.to_excel(writer, sheet_name='Monthly Revenue', index=False)
            office_breakdown.to_excel(writer, sheet_name='Office Revenue', index=False)
            
            # Sheet 6: Expenses
            df_expenses_filtered.to_excel(writer, sheet_name='Expenses', index=False)
        
        st.download_button(
            label="📥 Download Excel Report",
            data=buffer,
            file_name=f"IELTS_PTE_Report_{datetime.now().date()}.xlsx",
            mime="application/vnd.ms-excel"
        )
        
        # Email Section
        st.subheader("📧 Send Email Report")
        
        config = load_config()
        

        st.write("Generate and send comprehensive financial report via email")
        
        
        # Get period name for email subject based on selected date range
        period_name = f"{start_date.strftime('%b %Y')} to {end_date.strftime('%b %Y')}"
        if start_date.month == end_date.month and start_date.year == end_date.year:
            period_name = start_date.strftime('%B %Y')  # Same month
        
        # 1. Calculate LATEST MONTH specific metrics (Card 1 & 3)
        # We use the end_date of the selection as the "Latest Month"
        target_latest_month = end_date.strftime('%Y-%m')
        target_latest_month_name = end_date.strftime('%B %Y')
        
        # Filter for just this specific month
        df_latest_month_payments = df_payments[df_payments['MonthYear'] == target_latest_month]
        df_latest_month_expenses_data = df_expenses[df_expenses['MonthYear'] == target_latest_month]
        
        latest_card_revenue = df_latest_month_payments['Paid Amount'].sum()
        latest_card_expenses = df_latest_month_expenses_data['Amount'].sum()
        
        # 2. Calculate TOTAL Range metrics (Card 2 & 4)
        total_range_revenue = df_payments_filtered['Paid Amount'].sum()
        total_range_expenses = df_expenses_filtered['Amount'].sum()
        
        # Get total date range text
        date_range_text = f"{start_date.strftime('%b %d, %Y')} to {end_date.strftime('%b %d, %Y')}"
        
        # Auto-generate smart subject
        default_subject = f"IELTS/PTE Financial Report - {period_name}"
        
        # Email configuration in sidebar
        with st.sidebar:
            st.header("Email Configuration")
            default_email = config.get("sender_email", "")
            default_password = config.get("sender_password", "")
            
            sender_email = st.text_input("Sender Email", value=default_email, key="ielts_sender")
            sender_password = st.text_input("App Password", value=default_password, type="password", key="ielts_pass")
            st.info("Using same email config as Visa Report")
        
        default_recipients = config.get("recipients", "")
        recipients = st.text_input("Recipients (comma separated)", value=default_recipients, key="ielts_recipients")
        
        # Get the actual latest month from payments data (for expenses reference if needed, but we use selection now)
        latest_payment_month = df_payments['MonthYear'].max()
        
        email_subject = st.text_input("Email Subject", default_subject)
        
        # Calculate monthly expenses for cards (this is for the FILTERED period, used in dashboard)
        filtered_period_expenses = df_expenses_filtered['Amount'].sum()
        profit_emoji = "✅" if total_profit > 0 else "⚠️" if total_profit < 0 else "➖"
        
        # Create compact HTML email with 5 financial cards IN 1 ROW
        # Prepare expenses breakdown for email
        # Prepare expenses breakdown for email
        if not df_expenses_filtered.empty:
            expenses_breakdown = df_expenses_filtered[['Office', 'Teacher Name', 'Amount', 'Month']].copy()
            expenses_breakdown['Month'] = pd.to_datetime(expenses_breakdown['Month']).dt.strftime('%B %Y')
            expenses_by_office = expenses_breakdown.groupby('Office').agg({
                'Amount': 'sum',
                'Teacher Name': lambda x: ', '.join(x.unique())
            }).reset_index()
            expenses_table_html = expenses_breakdown.to_html(index=False, border=0)
            # Add simple inline styles to the pandas html table if possible, or wrap it
            expenses_table_html = expenses_table_html.replace('<table border="0" class="dataframe">', '<table style="width:100%; border-collapse:collapse; font-size:13px;">')
            expenses_table_html = expenses_table_html.replace('<th>', '<th style="background-color:#3498db; color:white; padding:6px; text-align:left;">')
            expenses_table_html = expenses_table_html.replace('<td>', '<td style="border:1px solid #ddd; padding:5px;">')
        else:
            expenses_table_html = '<p style="color:gray">No expense data for selected period</p>'
        
        # Include current time in subject to prevent Gmail threading/collapsing
        current_time_str = datetime.now().strftime("%H:%M:%S")
        if f"({current_time_str[:5]})" not in period_name:
             # Use HH:MM in subject, full seconds in body
             default_subject = f"IELTS/PTE Financial Report - {period_name} ({current_time_str[:5]})"

        # Zero-width uniqueness hack: Add a variable number of zero-width spaces to the greeting
        import random
        zero_width_spaces = "&zwnj;" * random.randint(1, 10)
        
        html_body = f"""<html><head><style>
        body{{font-family:Arial,sans-serif;font-size:14px;line-height:1.4;color:#333; margin:0; padding:0;}}
        h2{{color:#2c3e50;font-size:16px;margin:12px 0 8px 0;border-bottom:2px solid #3498db;padding-bottom:4px}}
        table{{border-collapse:collapse;width:100%;margin:8px 0;font-size:13px}}
        th{{background-color:#3498db;color:white;padding:6px;text-align:left}}
        td{{border:1px solid #ddd;padding:5px}}
        tr:nth-child(even){{background-color:#f9f9f9}}
        
        .card-val{{font-size:15px; font-weight:bold; color:#2980b9; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}}
        .card-lbl{{font-size:9px; color:#555; margin-top:3px; line-height:1.1;}}
        </style></head><body>
<div style="font-family:Arial,sans-serif;font-size:14px;line-height:1.4;color:#333;">
<p>Dear Team,{zero_width_spaces}</p>
<p>Kindly find attached the <strong>IELTS/PTE Financial Report for {period_name}</strong>.</p>
<h2>💰 Financial Summary</h2>

<table style="width:100%; border-collapse:separate; border-spacing:0; table-layout:fixed; border:none;">
    <tr>
        <td style="width:19%; background-color:#ecf0f1; border-radius:6px; padding:8px; text-align:center; vertical-align:top; border:none;">
            <div class="card-val">NPR {latest_card_revenue:,.0f}</div>
            <div class="card-lbl">📈 {target_latest_month_name}<br>Sales</div>
        </td>
        <td style="width:1.25%; border:none; background:none;"></td>
        <td style="width:19%; background-color:#ecf0f1; border-radius:6px; padding:8px; text-align:center; vertical-align:top; border:none;">
            <div class="card-val">NPR {total_range_revenue:,.0f}</div>
            <div class="card-lbl">💰 Total Sales<br><small>{date_range_text}</small></div>
        </td>
        <td style="width:1.25%; border:none; background:none;"></td>
        <td style="width:19%; background-color:#ecf0f1; border-radius:6px; padding:8px; text-align:center; vertical-align:top; border:none;">
            <div class="card-val">NPR {latest_card_expenses:,.0f}</div>
            <div class="card-lbl">💸 {target_latest_month_name}<br>Expenses</div>
        </td>
        <td style="width:1.25%; border:none; background:none;"></td>
        <td style="width:19%; background-color:#ecf0f1; border-radius:6px; padding:8px; text-align:center; vertical-align:top; border:none;">
            <div class="card-val">NPR {total_range_expenses:,.0f}</div>
            <div class="card-lbl">💳 Total<br>Expenses</div>
        </td>
        <td style="width:1.25%; border:none; background:none;"></td>
        <td style="width:19%; background-color:{'#d4edda' if total_profit>0 else '#f8d7da'}; border-radius:6px; padding:8px; text-align:center; vertical-align:top; border:none;">
            <div class="card-val" style="color:{'#155724' if total_profit>0 else '#c82333'}">NPR {total_profit:,.0f}</div>
            <div class="card-lbl">{profit_emoji} Profit/Loss</div>
        </td>
    </tr>
</table>

<h2>📈 Details</h2>
<table><tr><th>Metric</th><th>Value</th></tr>
<tr><td>Student Revenue</td><td>NPR {total_student_revenue:,.0f}</td></tr>
<tr><td>Book Revenue</td><td>NPR {total_book_revenue:,.0f}</td></tr>
<tr><td>Outstanding</td><td>NPR {total_outstanding:,.0f}</td></tr>
<tr><td>Total Students</td><td>{total_students}</td></tr>
</table>
<h2>💸 Expenses Breakdown</h2>
{expenses_table_html}
<h2>🏢 Office Performance</h2>
{office_breakdown.to_html(index=False, border=0)}
<p style="margin-top:15px">Please review the detailed Excel report attached.</p>
<p>Best regards,<br><strong>Ashish Shrestha</strong></p>
<div style="color:#ffffff; font-size:1px; line-height:1px; opacity:0.01; user-select:none;">Ref: {current_time_str}</div>
</div>
</body></html>"""
        
        # Show email preview BEFORE the send button
        st.subheader("📧 Email Preview")
        with st.expander("Click to preview email content", expanded=True):
            st.markdown(f"**Subject:** {email_subject}")
            # st.markdown("**To:** " + recipients) # Removed as per user request
            # st.divider() # Removed as per user request
            st.components.v1.html(html_body, height=800, scrolling=True)
        
        if st.button("🚀 Send Email with Report", type="primary"):
            if not sender_email or not sender_password:
                st.error("Please configure email settings in the sidebar")
            else:
                try:
                    import smtplib
                    from email.mime.multipart import MIMEMultipart
                    from email.mime.text import MIMEText
                    from email.mime.base import MIMEBase
                    from email import encoders
                    
                    # Setup MIME
                    msg = MIMEMultipart('alternative')
                    msg['From'] = sender_email
                    msg['To'] = recipients
                    msg['Subject'] = email_subject
                    
                    # Attach HTML body
                    msg.attach(MIMEText(html_body, 'html'))
                    
                    # Attach Excel file
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(buffer.getvalue())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f"attachment; filename= IELTS_PTE_Report_{datetime.now().date()}.xlsx")
                    msg.attach(part)
                    
                    # Send email
                    server = smtplib.SMTP('smtp.gmail.com', 587)
                    server.starttls()
                    server.login(sender_email, sender_password)
                    
                    recipient_list = [r.strip() for r in recipients.split(',')]
                    server.sendmail(sender_email, recipient_list, msg.as_string())
                    server.quit()
                    
                    st.success(f"✅ Email sent successfully to: {recipients}!")
                    
                except Exception as e:
                    st.error(f"Failed to send email. Error: {e}")
        
        
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.info("Please check if the Google Sheets are published and accessible.")
