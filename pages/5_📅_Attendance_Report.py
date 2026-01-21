import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta
import plotly.graph_objects as go
import plotly.express as px
import calendar
import io

# PAGE SETUP
st.set_page_config(page_title="Attendance - Monthly Overview", page_icon="📅", layout="wide")

# CUSTOM CSS FOR DARK CORPORATE THEME (MATCHING REFERENCE)
st.markdown("""
<style>
    /* Main container */
    .main {
        background-color: #1a1f2e;
    }
    
    /* Page title */
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
    
    /* Section Headers */
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
    
    /* KPI Cards */
    .kpi-card {
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        color: white;
        margin: 10px 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        min-height: 120px;
    }
    
    .kpi-green {
        background: linear-gradient(135deg, #27ae60 0%, #229954 100%);
    }
    
    .kpi-blue {
        background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
    }
    
    .kpi-red {
        background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
    }
    
    .kpi-orange {
        background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%);
    }
    
    .kpi-number {
        font-size: 42px;
        font-weight: bold;
        margin: 10px 0;
    }
    
    .kpi-label {
        font-size: 13px;
        opacity: 0.95;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Tables */
    .dataframe {
        font-size: 13px;
    }
    
    /* Calendar styling */
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
</style>
""", unsafe_allow_html=True)

# TITLE
st.markdown("<div class='page-title'>📅 Employee Attendance - Monthly Overview</div>", unsafe_allow_html=True)
st.markdown("<p class='page-subtitle'>Work Hours: 9:30 AM – 6:00 PM</p>", unsafe_allow_html=True)

# BUSINESS RULES (CONSTANTS)
WORK_START_TIME = time(9, 30)
REQUIRED_HOURS = 8.0
LATE_THRESHOLD = time(9, 30)
CHRONIC_LATE_THRESHOLD = 0.20  # 20% of days

# ========================================
# DATA PROCESSING FUNCTION (SIMPLIFIED)
# ========================================

def process_attendance_simple(df):
    """
    Process raw attendance data using simplified logic:
    - First IN = earliest punch of the day
    - Last OUT = latest punch of the day
    - Total Work Time = Last OUT - First IN
    - Late = First IN > 9:30 AM
    - Early Exit = Total Work Time < 8 hours
    """
    
    # Standardize column names
    df.columns = df.columns.str.strip()
    
    # Find relevant columns
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
    
    # Parse the combined Date/Time column
    df['Timestamp'] = pd.to_datetime(df[datetime_col], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['Timestamp'])
    
    # Extract date and employee
    df['Date'] = df['Timestamp'].dt.date
    df['Employee'] = df[name_col].astype(str).str.strip()
    
    # Process each employee-date combination
    results = []
    grouped = df.groupby(['Employee', 'Date'])
    
    for (emp, date), group in grouped:
        punches = group['Timestamp'].sort_values()
        
        if len(punches) < 1:
            continue
        
        first_in = punches.iloc[0]
        last_out = punches.iloc[-1]
        
        # Calculate total work time in hours
        work_hours = (last_out - first_in).total_seconds() / 3600
        
        # Determine flags
        is_late = first_in.time() > LATE_THRESHOLD
        is_early_exit = work_hours < REQUIRED_HOURS
        is_compliant = work_hours >= REQUIRED_HOURS and not is_late
        
        results.append({
            'Employee': emp,
            'Date': date,
            'FirstIn': first_in,
            'LastOut': last_out,
            'WorkHours': work_hours,
            'IsLate': is_late,
            'IsEarlyExit': is_early_exit,
            'IsCompliant': is_compliant
        })
    
    return pd.DataFrame(results)

# ========================================
# FILE UPLOAD
# ========================================

uploaded_file = st.file_uploader("📤 Upload Excel Attendance Sheet", type=['xlsx', 'xls', 'csv'])

if uploaded_file is not None:
    try:
        # Load file
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
        
        # Process attendance data
        df_daily = process_attendance_simple(df_raw)
        
        if df_daily is not None and len(df_daily) > 0:
            st.success(f"✅ Loaded {len(df_daily)} attendance records for {df_daily['Employee'].nunique()} employees")
            
            # Get month info
            dates = pd.to_datetime(df_daily['Date'])
            month_name = dates.dt.strftime('%B %Y').mode()[0]
            total_days_in_month = dates.dt.day.max()
            
            # Calculate employee-level metrics
            employee_stats = df_daily.groupby('Employee').agg({
                'Date': 'count',  # Present days
                'WorkHours': 'mean',  # Average work hours
                'IsLate': 'sum',  # Late days
                'IsEarlyExit': 'sum',  # Early exit days
                'IsCompliant': 'sum'  # Compliant days
            }).reset_index()
            
            employee_stats.columns = ['Employee', 'PresentDays', 'AvgWorkHours', 'LateDays', 'EarlyExitDays', 'CompliantDays']
            employee_stats['AttendancePct'] = (employee_stats['PresentDays'] / total_days_in_month * 100).round(1)
            employee_stats['ChronicLate'] = (employee_stats['LateDays'] / employee_stats['PresentDays']) >= CHRONIC_LATE_THRESHOLD
            employee_stats['UnderHours'] = employee_stats['AvgWorkHours'] < REQUIRED_HOURS
            employee_stats['AvgDeviation'] = (employee_stats['AvgWorkHours'] - REQUIRED_HOURS).round(1)
            employee_stats['TotalRiskDays'] = employee_stats['LateDays'] + employee_stats['EarlyExitDays']
            employee_stats['RiskLevel'] = employee_stats['TotalRiskDays'].apply(
                lambda x: 'High Risk' if x > 10 else ('Warning' if x > 5 else 'Compliant')
            )
            
            # ========================================
            # SECTION 1: MONTHLY MANAGEMENT SNAPSHOT
            # ========================================
            
            st.markdown("<div class='section-header'>Monthly Management Snapshot</div>", unsafe_allow_html=True)
            
            col1, col2, col3, col4 = st.columns(4)
            
            # Card 1: Avg Attendance %
            with col1:
                avg_attendance = employee_stats['AttendancePct'].mean()
                st.markdown(f"""
                <div class='kpi-card kpi-green'>
                    <div class='kpi-label'>Avg Attendance</div>
                    <div class='kpi-number'>{int(avg_attendance)}%</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Card 2: Average Net Work Hrs
            with col2:
                avg_work_hrs = employee_stats['AvgWorkHours'].mean()
                st.markdown(f"""
                <div class='kpi-card kpi-blue'>
                    <div class='kpi-label'>Average Net Work Hrs</div>
                    <div class='kpi-number'>{avg_work_hrs:.1f} hrs</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Card 3: Chronic Late %
            with col3:
                chronic_late_pct = (employee_stats['ChronicLate'].sum() / len(employee_stats) * 100)
                st.markdown(f"""
                <div class='kpi-card kpi-red'>
                    <div class='kpi-label'>Chronic Late</div>
                    <div class='kpi-number'>{int(chronic_late_pct)}%</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Card 4: Under Hours %
            with col4:
                under_hours_pct = (employee_stats['UnderHours'].sum() / len(employee_stats) * 100)
                st.markdown(f"""
                <div class='kpi-card kpi-orange'>
                    <div class='kpi-label'>Under</div>
                    <div class='kpi-number'>{int(under_hours_pct)}%</div>
                </div>
                """, unsafe_allow_html=True)
            
            # ========================================
            # MAIN LAYOUT: LEFT PANEL + RIGHT PANEL
            # ========================================
            
            col_left, col_right = st.columns([2.5, 1.5])
            
            with col_left:
                # ========================================
                # SECTION 2: TOP 5 BEST COMPLIANT EMPLOYEES
                # ========================================
                
                st.markdown("<div class='section-header'>Top 5 Best Compliant Employees</div>", unsafe_allow_html=True)
                
                top_compliant = employee_stats.nlargest(5, 'AvgWorkHours')[['Employee', 'AvgWorkHours', 'AvgDeviation']].copy()
                top_compliant['AvgWorkHours'] = top_compliant['AvgWorkHours'].round(1)
                top_compliant.columns = ['Employee', 'Avg Net Work Hrs', 'Avg Deviation']
                
                def color_work_hours(val):
                    if val >= 8.0:
                        return 'background-color: #27ae60; color: white; font-weight: bold;'
                    else:
                        return ''
                
                def color_deviation(val):
                    if val < 0:
                        return 'background-color: #f39c12; color: white; font-weight: bold;'
                    else:
                        return ''
                
                styled_compliant = top_compliant.style.applymap(color_work_hours, subset=['Avg Net Work Hrs']) \
                                                      .applymap(color_deviation, subset=['Avg Deviation'])
                
                st.dataframe(styled_compliant, use_container_width=True, height=250)
                
                # ========================================
                # SECTION 3: TOP 5 RISK EMPLOYEES
                # ========================================
                
                st.markdown("<div class='section-header'>Top 5 Risk Employees</div>", unsafe_allow_html=True)
                
                top_risk = employee_stats.nlargest(5, 'TotalRiskDays')[['Employee', 'LateDays', 'EarlyExitDays', 'TotalRiskDays']].copy()
                top_risk['UnderDays'] = top_risk['EarlyExitDays']  # Add under days column
                top_risk = top_risk[['Employee', 'LateDays', 'EarlyExitDays', 'UnderDays', 'TotalRiskDays']]
                top_risk.columns = ['Employee', 'Late Days', 'Early Days', 'Under Days', 'Total Risk Days']
                
                def color_late_days(val):
                    if val > 10:
                        return 'background-color: #e74c3c; color: white; font-weight: bold;'
                    elif val > 5:
                        return 'background-color: #f39c12; color: white; font-weight: bold;'
                    else:
                        return ''
                
                def color_risk_total(val):
                    if val > 15:
                        return 'background-color: #e74c3c; color: white; font-weight: bold;'
                    elif val > 10:
                        return 'background-color: #f39c12; color: white; font-weight: bold;'
                    else:
                        return ''
                
                styled_risk = top_risk.style.applymap(color_late_days, subset=['Late Days']) \
                                            .applymap(color_risk_total, subset=['Total Risk Days'])
                
                st.dataframe(styled_risk, use_container_width=True, height=250)
                
                # ========================================
                # SECTION 4: MONTHLY EMPLOYEE COMPLIANCE TABLE
                # ========================================
                
                st.markdown("<div class='section-header'>Monthly Employee Compliance Table</div>", unsafe_allow_html=True)
                
                compliance_table = employee_stats[['Employee', 'PresentDays', 'LateDays', 'EarlyExitDays', 'RiskLevel']].copy()
                compliance_table.columns = ['Employee', 'Present Days', 'Late Days', 'Bec', 'Risk']
                
                def color_risk_row(row):
                    if row['Risk'] == 'High Risk':
                        return ['background-color: #e74c3c; color: white'] * len(row)
                    elif row['Risk'] == 'Warning':
                        return ['background-color: #f39c12; color: white'] * len(row)
                    else:
                        return ['background-color: #27ae60; color: white'] * len(row)
                
                styled_compliance = compliance_table.style.apply(color_risk_row, axis=1)
                
                st.dataframe(styled_compliance, use_container_width=True, height=300)
                
                # ========================================
                # SECTION 5: MONTHLY PATTERN ANALYSIS
                # ========================================
                
                st.markdown("<div class='section-header'>Monthly Pattern Analysis</div>", unsafe_allow_html=True)
                
                chart_col1, chart_col2 = st.columns(2)
                
                with chart_col1:
                    st.markdown("**Late Days Trend**")
                    
                    # Count late employees per day
                    late_by_date = df_daily[df_daily['IsLate']].groupby('Date').size().reset_index(name='Count')
                    late_by_date['Day'] = pd.to_datetime(late_by_date['Date']).dt.day
                    
                    fig_late = go.Figure()
                    fig_late.add_trace(go.Bar(
                        x=late_by_date['Day'],
                        y=late_by_date['Count'],
                        marker_color='#f39c12',
                        name='Late Employees'
                    ))
                    
                    fig_late.update_layout(
                        height=250,
                        margin=dict(l=20, r=20, t=20, b=20),
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='white', size=10),
                        xaxis=dict(title='Day of Month', showgrid=False),
                        yaxis=dict(title='Count', showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
                        showlegend=False
                    )
                    
                    st.plotly_chart(fig_late, use_container_width=True, config={'displayModeBar': False})
                
                with chart_col2:
                    st.markdown("**Avg Check-In Time Distribution**")
                    
                    # Create time bins
                    df_daily['CheckInHour'] = df_daily['FirstIn'].dt.hour + df_daily['FirstIn'].dt.minute / 60
                    
                    fig_checkin = go.Figure()
                    fig_checkin.add_trace(go.Histogram(
                        x=df_daily['CheckInHour'],
                        marker_color='#3498db',
                        nbinsx=20,
                        name='Check-In Distribution'
                    ))
                    
                    fig_checkin.update_layout(
                        height=250,
                        margin=dict(l=20, r=20, t=20, b=20),
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='white', size=10),
                        xaxis=dict(title='Time', showgrid=False),
                        yaxis=dict(title='Employees', showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
                        showlegend=False
                    )
                    
                    st.plotly_chart(fig_checkin, use_container_width=True, config={'displayModeBar': False})
                
                # Net Work Hours Distribution (full width)
                st.markdown("**Net Work Hours Distribution**")
                
                # Categorize work hours
                df_daily['HoursCategory'] = df_daily['WorkHours'].apply(
                    lambda x: 'Compliant' if x >= 8 else ('Late/Short' if x >= 6 else 'Excess Day')
                )
                
                hours_by_date = df_daily.groupby(['Date', 'HoursCategory']).size().unstack(fill_value=0).reset_index()
                hours_by_date['Day'] = pd.to_datetime(hours_by_date['Date']).dt.day
                
                fig_hours = go.Figure()
                
                if 'Compliant' in hours_by_date.columns:
                    fig_hours.add_trace(go.Bar(
                        x=hours_by_date['Day'],
                        y=hours_by_date['Compliant'],
                        name='Compliant Day',
                        marker_color='#3498db'
                    ))
                
                if 'Late/Short' in hours_by_date.columns:
                    fig_hours.add_trace(go.Bar(
                        x=hours_by_date['Day'],
                        y=hours_by_date['Late/Short'],
                        name='Late / Short Day',
                        marker_color='#f39c12'
                    ))
                
                if 'Excess Day' in hours_by_date.columns:
                    fig_hours.add_trace(go.Bar(
                        x=hours_by_date['Day'],
                        y=hours_by_date['Excess Day'],
                        name='Excess Day',
                        marker_color='#e74c3c'
                    ))
                
                fig_hours.update_layout(
                    barmode='stack',
                    height=250,
                    margin=dict(l=20, r=20, t=20, b=20),
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white', size=10),
                    xaxis=dict(title='Day of Month', showgrid=False),
                    yaxis=dict(title='Employees', showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
                    legend=dict(
                        orientation='h',
                        yanchor='bottom',
                        y=-0.3,
                        xanchor='center',
                        x=0.5
                    )
                )
                
                st.plotly_chart(fig_hours, use_container_width=True, config={'displayModeBar': False})
            
            # ========================================
            # RIGHT PANEL: SECTION 6 - EMPLOYEE CALENDAR & STATS
            # ========================================
            
            with col_right:
                st.markdown("<div class='section-header'>Employee Calendar & Stats</div>", unsafe_allow_html=True)
                
                # Employee selector
                selected_employee = st.selectbox("Select Employee:", employee_stats['Employee'].unique(), key='emp_select')
                
                # Filter data for selected employee
                emp_data = df_daily[df_daily['Employee'] == selected_employee].copy()
                emp_summary = employee_stats[employee_stats['Employee'] == selected_employee].iloc[0]
                
                # Month selector
                available_months = pd.to_datetime(emp_data['Date']).dt.to_period('M').unique()
                if len(available_months) > 0:
                    selected_month = st.selectbox("Month:", [str(m) for m in available_months], key='month_select')
                    
                    # Calendar view
                    st.markdown("**Calendar**")
                    
                    # Parse selected month
                    year, month = map(int, selected_month.split('-'))
                    
                    # Get calendar for the month
                    cal = calendar.monthcalendar(year, month)
                    
                    # Create calendar HTML with separate header
                    weekdays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
                    
                    # Calendar container
                    calendar_html = "<div style='margin: 10px 0;'>"
                    
                    # Weekday header row
                    calendar_html += "<div style='display: grid; grid-template-columns: repeat(7, 1fr); gap: 5px; margin-bottom: 5px;'>"
                    for day in weekdays:
                        calendar_html += f"<div style='text-align: center; font-weight: bold; color: #95a5a6; padding: 8px; font-size: 11px; text-transform: uppercase;'>{day}</div>"
                    calendar_html += "</div>"
                    
                    # Calendar days grid
                    calendar_html += "<div class='calendar-grid'>"
                    
                    # Add calendar days
                    emp_data['DayNum'] = pd.to_datetime(emp_data['Date']).dt.day
                    
                    for week in cal:
                        for day in week:
                            if day == 0:
                                calendar_html += "<div class='calendar-day day-empty'>-</div>"
                            else:
                                # Check if employee worked that day
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
                            <span>Short Days</span>
                            <span style='font-weight: bold; color: #e74c3c;'>{int(emp_summary['EarlyExitDays'])}</span>
                        </div>
                        <div style='display: flex; justify-content: space-between; padding: 8px 0;'>
                            <span>Excess Days (under 8 hrs)</span>
                            <span style='font-weight: bold; color: #e74c3c;'>{int(emp_summary['TotalRiskDays'])}</span>
                        </div>
                    </div>
                    """
                    
                    st.markdown(summary_html, unsafe_allow_html=True)
                    
                    # Net Work Hours Distribution Heatmap
                    st.markdown("**Net Work Hours Distribution**")
                    
                    # Create bins for work hours
                    bins = [0, 6, 7, 7.5, 8, 8.5, 9, 100]
                    labels = ['< 6 hrs', '6-7 hrs', '7-7.5 hrs', '7.5-8 hrs', '8-8.5 hrs', '8.5-9 hrs', '> 9 hrs']
                    
                    emp_data['HoursBin'] = pd.cut(emp_data['WorkHours'], bins=bins, labels=labels, include_lowest=True)
                    
                    # Count by bin
                    hours_dist = emp_data['HoursBin'].value_counts().sort_index()
                    
                    # Create color-coded display
                    dist_html = "<div style='background: #2c3e50; padding: 15px; border-radius: 8px;'>"
                    
                    for label in labels:
                        count = hours_dist.get(label, 0)
                        if label in ['7.5-8 hrs', '8-8.5 hrs']:
                            color = '#27ae60'  # Green - compliant
                        elif label in ['6-7 hrs', '7-7.5 hrs', '8.5-9 hrs']:
                            color = '#f39c12'  # Orange - warning
                        else:
                            color = '#e74c3c'  # Red - risk
                        
                        dist_html += f"""
                        <div style='display: flex; justify-content: space-between; padding: 6px; margin: 3px 0; background: {color}; border-radius: 5px; color: white; font-size: 12px;'>
                            <span>{label}</span>
                            <span style='font-weight: bold;'>{int(count)}</span>
                        </div>
                        """
                    
                    dist_html += "</div>"
                    
                    st.markdown(dist_html, unsafe_allow_html=True)
        
        else:
            st.warning("⚠️ No valid attendance data found. Please check your file format.")
            
    except Exception as e:
        st.error(f"❌ Error processing file: {str(e)}")
        st.exception(e)

else:
    # Show instructions when no file is uploaded
    st.info("👆 Please upload an Excel attendance sheet to begin")
    
    st.markdown("### 📋 File Format Requirements")
    st.markdown("""
    Your Excel file should contain the following columns:
    - **Employee Name**
    - **Date/Time** (combined timestamp column)
    - **Status** (optional: C/In, C/Out, or similar)
    
    The system will automatically:
    - Use **First IN** (earliest punch) and **Last OUT** (latest punch) per day
    - Calculate total work time = Last OUT - First IN
    - Flag late entries (after 9:30 AM)
    - Flag early exits (< 8 hours work time)
    - Generate monthly compliance dashboard
    """)
    
    # Show sample data format
    st.markdown("### 📄 Sample Data Format")
    sample_data = pd.DataFrame({
        'Employee Name': ['John Doe', 'John Doe', 'John Doe', 'John Doe', 'Jane Smith', 'Jane Smith'],
        'Date/Time': ['21/01/2024 09:52:00', '21/01/2024 12:30:00', '21/01/2024 13:45:00', '21/01/2024 18:05:00', 
                      '21/01/2024 09:25:00', '21/01/2024 18:00:00'],
        'Status': ['C/In', 'C/Out', 'C/In', 'C/Out', 'C/In', 'C/Out']
    })
    st.dataframe(sample_data, use_container_width=True)
