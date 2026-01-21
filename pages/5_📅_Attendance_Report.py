import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta
import calendar
import io

# PAGE SETUP
st.set_page_config(page_title="Attendance - Monthly Overview", page_icon="📅", layout="wide")

# CUSTOM CSS
st.markdown("""
<style>
    .main {
        background-color: #1a1f2e;
    }
    
    .page-title {
        background: linear-gradient(135deg, #3d5a80 0%, #2c3e50 100%);
        color: white;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 10px;
        font-size: 28px;
        font-weight: bold;
    }
    
    .page-subtitle {
        text-align: center;
        color: #95a5a6;
        font-size: 14px;
        margin-top: -10px;
        margin-bottom: 20px;
    }
    
    .section-header {
        background: linear-gradient(135deg, #3d5a80 0%, #2c3e50 100%);
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        margin: 15px 0 10px 0;
        font-weight: bold;
        font-size: 16px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    
    /* Hide Streamlit default dialog styling */
    [data-testid="stDialog"] {
        background: rgba(0,0,0,0.85) !important;
    }
    
    .calendar-grid {
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 5px;
        margin: 10px 0;
    }
    
    .calendar-day {
        padding: 10px;
        text-align: center;
        border-radius: 5px;
        font-size: 12px;
        font-weight: bold;
    }
    
    .day-compliant {
        background-color: #27ae60;
        color: white;
    }
    
    .day-warning {
        background-color: #f39c12;
        color: white;
    }
    
    .day-risk {
        background-color: #e74c3c;
        color: white;
    }
    
    .day-empty {
        background-color: #34495e;
        color: #7f8c8d;
    }
    
   .employee-button {
        background: transparent;
        border: 1px solid #3498db;
        color: #3498db;
        padding: 8px 16px;
        border-radius: 5px;
        cursor: pointer;
        transition: all 0.2s;
    }
    
    .employee-button:hover {
        background: #3498db;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# TITLE
st.markdown("<div class='page-title'>📅 Employee Attendance - Monthly Overview</div>", unsafe_allow_html=True)
st.markdown("<p class='page-subtitle'>Work Hours: 9:30 AM – 6:00 PM</p>", unsafe_allow_html=True)

# CONSTANTS
WORK_START_TIME = time(9, 30)
REQUIRED_HOURS = 8.0
LATE_THRESHOLD = time(9, 30)
CHRONIC_LATE_THRESHOLD = 0.20

# DATA PROCESSING
def process_attendance_simple(df):
    df.columns = df.columns.str.strip()
    
    name_col = None
    datetime_col = None
    
    for col in df.columns:
        col_lower = col.lower()
        if 'name' in col_lower and 'department' not in col_lower:
            name_col = col
        elif 'date/time' in col_lower or 'datetime' in col_lower or ('date' in col_lower and 'time' in col_lower):
            datetime_col = col
    
    if not name_col or not datetime_col:
        st.error("⚠️ Could not find Name and Date/Time columns")
        return None
    
    df['Timestamp'] = pd.to_datetime(df[datetime_col], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['Timestamp'])
    df['Date'] = df['Timestamp'].dt.date
    df['Employee'] = df[name_col].astype(str).str.strip()
    
    results = []
    grouped = df.groupby(['Employee', 'Date'])
    
    for (emp, date), group in grouped:
        punches = group['Timestamp'].sort_values()
        
        if len(punches) < 1:
            continue
        
        first_in = punches.iloc[0]
        last_out = punches.iloc[-1]
        work_hours = (last_out - first_in).total_seconds() / 3600
        
        is_late = first_in.time() > LATE_THRESHOLD
        is_early_exit = work_hours < REQUIRED_HOURS
        is_compliant = work_hours >= REQUIRED_HOURS and not is_late
        
        if is_compliant:
            note = "Compliant"
        elif is_late and is_early_exit:
            note = "Late Entry & Early Exit"
        elif is_late:
            note = "Late Entry"
        elif is_early_exit:
            note = "Early Exit"
        else:
            note = "Compliant"
        
        results.append({
            'Employee': emp,
            'Date': date,
            'FirstIn': first_in,
            'LastOut': last_out,
            'WorkHours': work_hours,
            'IsLate': is_late,
            'IsEarlyExit': is_early_exit,
            'IsCompliant': is_compliant,
            'Note': note
        })
    
    return pd.DataFrame(results)

# MODAL DIALOG DEFINITIONS
@st.dialog("🔴 Chronic Late Employees (Late ≥20% of days)", width="large")
def show_chronic_late_modal(employee_stats):
    chronic_late_emps = employee_stats[employee_stats['ChronicLate']][['Employee', 'LateDays', 'PresentDays']].copy()
    chronic_late_emps['Late %'] = (chronic_late_emps['LateDays'] / chronic_late_emps['PresentDays'] * 100).round(1)
    
    st.dataframe(
        chronic_late_emps,
        use_container_width=True,
        height=400,
        hide_index=True
    )

@st.dialog("🟠 Employees Under 8 Hours Average", width="large")
def show_under_hours_modal(employee_stats):
    under_hours_emps = employee_stats[employee_stats['UnderHours']][['Employee', 'AvgWorkHours', 'PresentDays']].copy()
    under_hours_emps['AvgWorkHours'] = under_hours_emps['AvgWorkHours'].round(1)
    under_hours_emps.columns = ['Employee', 'Avg Work Hours', 'Present Days']
    
    st.dataframe(
        under_hours_emps,
        use_container_width=True,
        height=400,
        hide_index=True
    )

@st.dialog("👤 Employee Attendance Details", width="large")
def show_employee_details_modal(df_daily, employee_name):
    st.subheader(f"{employee_name}")
    
    emp_records = df_daily[df_daily['Employee'] == employee_name].copy()
    emp_records['Date'] = pd.to_datetime(emp_records['Date']).dt.strftime('%Y-%m-%d')
    emp_records['Entry'] = emp_records['FirstIn'].dt.strftime('%H:%M:%S')
    emp_records['Exit'] = emp_records['LastOut'].dt.strftime('%H:%M:%S')
    emp_records['Working Hours'] = emp_records['WorkHours'].round(2)
    
    detail_table = emp_records[['Employee', 'Date', 'Entry', 'Exit', 'Working Hours', 'Note']]
    
    st.dataframe(
        detail_table,
        use_container_width=True,
        height=500,
        hide_index=True
    )

# FILE UPLOAD
uploaded_file = st.file_uploader("📤 Upload Excel Attendance Sheet", type=['xlsx', 'xls', 'csv'])

if uploaded_file is not None:
    try:
        file_name = uploaded_file.name.lower()
        
        if file_name.endswith('.csv'):
            df_raw = pd.read_csv(uploaded_file)
        elif file_name.endswith('.xls'):
            df_raw = pd.read_excel(uploaded_file, engine='xlrd')
        elif file_name.endswith('.xlsx'):
            df_raw = pd.read_excel(uploaded_file, engine='openpyxl')
        else:
            st.error("⚠️ Unsupported file format")
            st.stop()
        
        df_daily = process_attendance_simple(df_raw)
        
        if df_daily is not None and len(df_daily) > 0:
            st.success(f"✅ Loaded {len(df_daily)} attendance records for {df_daily['Employee'].nunique()} employees")
            
            # Calculate metrics
            dates = pd.to_datetime(df_daily['Date'])
            month_name = dates.dt.strftime('%B %Y').mode()[0]
            total_days_in_month = dates.dt.day.max()
            
            employee_stats = df_daily.groupby('Employee').agg({
                'Date': 'count',
                'WorkHours': 'mean',
                'IsLate': 'sum',
                'IsEarlyExit': 'sum',
                'IsCompliant': 'sum'
            }).reset_index()
            
            employee_stats.columns = ['Employee', 'PresentDays', 'AvgWorkHours', 'LateDays', 'EarlyExitDays', 'CompliantDays']
            employee_stats['AttendancePct'] = (employee_stats['PresentDays'] / total_days_in_month * 100).round(1)
            employee_stats['ChronicLate'] = (employee_stats['LateDays'] / employee_stats['PresentDays']) >= CHRONIC_LATE_THRESHOLD
            employee_stats['UnderHours'] = employee_stats['AvgWorkHours'] < REQUIRED_HOURS
            employee_stats['AvgDeviation'] = (employee_stats['AvgWorkHours'] - REQUIRED_HOURS).round(1)
            employee_stats['TotalRiskDays'] = employee_stats['LateDays'] + employee_stats['EarlyExitDays']
            
            # KPI CARDS
            st.markdown("<div class='section-header'>Monthly Management Snapshot</div>", unsafe_allow_html=True)
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                avg_attendance = employee_stats['AttendancePct'].mean()
                st.markdown(f"""
                <div style='padding: 20px; border-radius: 10px; text-align: center; color: white; background: linear-gradient(135deg, #27ae60 0%, #229954 100%); box-shadow: 0 4px 6px rgba(0,0,0,0.3); min-height: 120px;'>
                    <div style='font-size: 13px; opacity: 0.95; text-transform: uppercase; letter-spacing: 0.5px;'>AVG ATTENDANCE</div>
                    <div style='font-size: 42px; font-weight: bold; margin: 10px 0;'>{int(avg_attendance)}%</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                avg_work_hrs = employee_stats['AvgWorkHours'].mean()
                st.markdown(f"""
                <div style='padding: 20px; border-radius: 10px; text-align: center; color: white; background: linear-gradient(135deg, #3498db 0%, #2980b9 100%); box-shadow: 0 4px 6px rgba(0,0,0,0.3); min-height: 120px;'>
                    <div style='font-size: 13px; opacity: 0.95; text-transform: uppercase; letter-spacing: 0.5px;'>AVERAGE NET WORK HRS</div>
                    <div style='font-size: 42px; font-weight: bold; margin: 10px 0;'>{avg_work_hrs:.1f} hrs</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                chronic_late_pct = (employee_stats['ChronicLate'].sum() / len(employee_stats) * 100)
                
                # Create HTML card that looks identical to card 1 & 2
                st.markdown(f"""
                <div onclick="document.getElementById('chronic_btn_hidden').click()" style='padding: 20px; border-radius: 10px; text-align: center; color: white; background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%); box-shadow: 0 4px 6px rgba(0,0,0,0.3); min-height: 120px; cursor: pointer; transition: transform 0.2s;' onmouseover="this.style.transform='scale(1.05)'; this.style.boxShadow='0 6px 12px rgba(0,0,0,0.4)';" onmouseout="this.style.transform='scale(1)'; this.style.boxShadow='0 4px 6px rgba(0,0,0,0.3)';">
                    <div style='font-size: 13px; opacity: 0.95; text-transform: uppercase; letter-spacing: 0.5px;'>CHRONIC LATE</div>
                    <div style='font-size: 42px; font-weight: bold; margin: 10px 0;'>{int(chronic_late_pct)}%</div>
                    <div style='font-size: 10px; opacity: 0.7; margin-top: 5px;'>👆 Click for details</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Hidden button for Streamlit callback
                if st.button("chronic", key='chronic_late_btn', type="secondary", help="Hidden", disabled=False, use_container_width=False):
                    show_chronic_late_modal(employee_stats)
                
                # Hide the button with CSS
                st.markdown("""
                <style>
                button[kind="secondary"][key="chronic_late_btn"] {
                    display: none !important;
                }
                </style>
                <script>
                const chronicBtn = document.getElementById('chronic_btn_hidden');
                if (!chronicBtn) {
                    const buttons = Array.from(document.querySelectorAll('button'));
                    const targetBtn = buttons.find(btn => btn.innerText === 'chronic');
                    if (targetBtn) {
                        targetBtn.id = 'chronic_btn_hidden';
                        targetBtn.style.display = 'none';
                    }
                }
                </script>
                """, unsafe_allow_html=True)
            
            with col4:
                under_hours_pct = (employee_stats['UnderHours'].sum() / len(employee_stats) * 100)
                
                # Create HTML card that looks identical to card 1 & 2
                st.markdown(f"""
                <div onclick="document.getElementById('under_btn_hidden').click()" style='padding: 20px; border-radius: 10px; text-align: center; color: white; background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%); box-shadow: 0 4px 6px rgba(0,0,0,0.3); min-height: 120px; cursor: pointer; transition: transform 0.2s;' onmouseover="this.style.transform='scale(1.05)'; this.style.boxShadow='0 6px 12px rgba(0,0,0,0.4)';" onmouseout="this.style.transform='scale(1)'; this.style.boxShadow='0 4px 6px rgba(0,0,0,0.3)';">
                    <div style='font-size: 13px; opacity: 0.95; text-transform: uppercase; letter-spacing: 0.5px;'>UNDER 8HRS</div>
                    <div style='font-size: 42px; font-weight: bold; margin: 10px 0;'>{int(under_hours_pct)}%</div>
                    <div style='font-size: 10px; opacity: 0.7; margin-top: 5px;'>👆 Click for details</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Hidden button for Streamlit callback
                if st.button("under", key='under_hours_btn', type="secondary", help="Hidden", disabled=False, use_container_width=False):
                    show_under_hours_modal(employee_stats)
                
                # Hide the button with CSS
                st.markdown("""
                <style>
                button[kind="secondary"][key="under_hours_btn"] {
                    display: none !important;
                }
                </style>
                <script>
                const underBtn = document.getElementById('under_btn_hidden');
                if (!underBtn) {
                    const buttons = Array.from(document.querySelectorAll('button'));
                    const targetBtn = buttons.find(btn => btn.innerText === 'under');
                    if (targetBtn) {
                        targetBtn.id = 'under_btn_hidden';
                        targetBtn.style.display = 'none';
                    }
                }
                </script>
                """, unsafe_allow_html=True)
            
            # MAIN LAYOUT
            col_left, col_right = st.columns([2.5, 1.5])
            
            with col_left:
                # TOP 5 BEST COMPLIANT
                st.markdown("<div class='section-header'>Top 5 Best Compliant Employees</div>", unsafe_allow_html=True)
                st.caption("Click on employee name to see attendance details:")
                
                top_compliant = employee_stats.nlargest(5, 'AvgWorkHours')[['Employee', 'AvgWorkHours', 'AvgDeviation']].copy()
                top_compliant['AvgWorkHours'] = top_compliant['AvgWorkHours'].round(1)
                
                for idx, row in top_compliant.iterrows():
                    col_name, col_hours, col_dev = st.columns([2, 1, 1])
                    with col_name:
                        if st.button(f"👤 {row['Employee']}", key=f"best_{idx}", use_container_width=True):
                            show_employee_details_modal(df_daily, row['Employee'])
                    with col_hours:
                        st.metric("Avg Hours", f"{row['AvgWorkHours']:.1f}")
                    with col_dev:
                        st.metric("Deviation", f"{row['AvgDeviation']:.1f}")
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # TOP 5 RISK EMPLOYEES
                st.markdown("<div class='section-header'>Top 5 Risk Employees</div>", unsafe_allow_html=True)
                st.caption("Click on employee name to see attendance details:")
                
                top_risk = employee_stats.nlargest(5, 'TotalRiskDays')[['Employee', 'LateDays', 'EarlyExitDays', 'TotalRiskDays']].copy()
                
                for idx, row in top_risk.iterrows():
                    col_name, col_late, col_early, col_total = st.columns([2, 1, 1, 1])
                    with col_name:
                        if st.button(f"⚠️ {row['Employee']}", key=f"risk_{idx}", use_container_width=True):
                            show_employee_details_modal(df_daily, row['Employee'])
                    with col_late:
                        st.metric("Late", int(row['LateDays']))
                    with col_early:
                        st.metric("Early Exit", int(row['EarlyExitDays']))
                    with col_total:
                        st.metric("Total Risk", int(row['TotalRiskDays']))
            
            # RIGHT PANEL - EMPLOYEE CALENDAR & STATS
            with col_right:
                st.markdown("<div class='section-header'>Employee Calendar & Stats</div>", unsafe_allow_html=True)
                
                selected_employee = st.selectbox("Select Employee:", employee_stats['Employee'].unique(), key='emp_select')
                
                emp_data = df_daily[df_daily['Employee'] == selected_employee].copy()
                emp_summary = employee_stats[employee_stats['Employee'] == selected_employee].iloc[0]
                
                available_months = pd.to_datetime(emp_data['Date']).dt.to_period('M').unique()
                if len(available_months) > 0:
                    selected_month = st.selectbox("Month:", [str(m) for m in available_months], key='month_select')
                    
                    st.markdown("**Calendar**")
                    
                    year, month = map(int, selected_month.split('-'))
                    cal = calendar.monthcalendar(year, month)
                    weekdays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
                    
                    calendar_html = "<div style='margin: 10px 0;'>"
                    calendar_html += "<div style='display: grid; grid-template-columns: repeat(7, 1fr); gap: 5px; margin-bottom: 5px;'>"
                    for day in weekdays:
                        calendar_html += f"<div style='text-align: center; font-weight: bold; color: #95a5a6; padding: 8px; font-size: 11px; text-transform: uppercase;'>{day}</div>"
                    calendar_html += "</div>"
                    
                    calendar_html += "<div class='calendar-grid'>"
                    emp_data['DayNum'] = pd.to_datetime(emp_data['Date']).dt.day
                    
                    for week in cal:
                        for day in week:
                            if day == 0:
                                calendar_html += "<div class='calendar-day day-empty'>-</div>"
                            else:
                                day_record = emp_data[emp_data['DayNum'] == day]
                                
                                if len(day_record) > 0:
                                    record = day_record.iloc[0]
                                    if record['IsCompliant']:
                                        css_class = 'day-compliant'
                                    elif record['IsLate'] or record['IsEarlyExit']:
                                        css_class = 'day-warning'
                                    else:
                                        css_class = 'day-risk'
                                else:
                                    css_class = 'day-empty'
                                
                                calendar_html += f"<div class='calendar-day {css_class}'>{day}</div>"
                    
                    calendar_html += "</div></div>"
                    st.markdown(calendar_html, unsafe_allow_html=True)
                    
                    # Month Summary
                    st.markdown("**Month Summary**")
                    summary_html = f"""
                    <div style='background: #2c3e50; padding: 15px; border-radius: 8px; color: white;'>
                        <div style='display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.1);'>
                            <span>Present Days</span>
                            <span style='font-weight: bold;'>{int(emp_summary['PresentDays'])}</span>
                        </div>
                        <div style='display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.1);'>
                            <span>Late Days</span>
                            <span style='font-weight: bold; color: #f39c12;'>{int(emp_summary['LateDays'])}</span>
                        </div>
                        <div style='display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.1);'>
                            <span>Early Exit Days</span>
                            <span style='font-weight: bold; color: #e74c3c;'>{int(emp_summary['EarlyExitDays'])}</span>
                        </div>
                        <div style='display: flex; justify-content: space-between; padding: 8px 0;'>
                            <span>Avg Work Hours</span>
                            <span style='font-weight: bold; color: #3498db;'>{emp_summary['AvgWorkHours']:.1f} hrs</span>
                        </div>
                    </div>
                    """
                    st.markdown(summary_html, unsafe_allow_html=True)
        
        else:
            st.warning("⚠️ No valid attendance data found.")
            
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        st.exception(e)

else:
    st.info("👆 Please upload an Excel attendance sheet to begin")
    
    st.markdown("### 📋 File Format Requirements")
    st.markdown("""
    - **Employee Name**
    - **Date/Time** (timestamp)
    - **Status** (optional)
    
    System calculates:
    - First IN (earliest punch) & Last OUT (latest punch)
    - Total work time = Last OUT - First IN
    - Late if after 9:30 AM, Early Exit if < 8 hours
    """)
