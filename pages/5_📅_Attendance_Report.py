import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta
import plotly.graph_objects as go
import plotly.express as px
import io

# PAGE SETUP
st.set_page_config(page_title="Attendance Report", page_icon="📅", layout="wide")

# CUSTOM CSS FOR DARK CORPORATE THEME
st.markdown("""
<style>
    /* Main container */
    .main {
        background-color: #1a1f2e;
    }
    
    /* KPI Cards */
    .kpi-card {
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        color: white;
        margin: 10px 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    
    .kpi-red {
        background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
    }
    
    .kpi-orange {
        background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%);
    }
    
    .kpi-blue {
        background: linear-gradient(135deg, #3b4a6b 0%, #2c3e50 100%);
    }
    
    .kpi-number {
        font-size: 48px;
        font-weight: bold;
        margin: 10px 0;
    }
    
    .kpi-label {
        font-size: 14px;
        opacity: 0.9;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Section Headers */
    .section-header {
        background: linear-gradient(135deg, #34495e 0%, #2c3e50 100%);
        color: white;
        padding: 15px 20px;
        border-radius: 8px;
        margin: 20px 0 10px 0;
        font-weight: bold;
        font-size: 18px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    
    /* List styling */
    .top-list {
        background: #2c3e50;
        padding: 15px;
        border-radius: 8px;
        color: white;
        min-height: 200px;
    }
    
    .top-list-item {
        padding: 8px 0;
        border-bottom: 1px solid rgba(255,255,255,0.1);
        font-size: 14px;
    }
    
    /* Table styling */
    .compliance-table {
        width: 100%;
        border-collapse: collapse;
        margin: 10px 0;
    }
    
    .compliance-table th {
        background: #34495e;
        color: white;
        padding: 12px;
        text-align: left;
        font-weight: bold;
    }
    
    .compliance-table td {
        padding: 10px 12px;
        border-bottom: 1px solid #34495e;
    }
    
    .cell-red {
        background-color: #e74c3c !important;
        color: white;
        font-weight: bold;
        padding: 8px;
        border-radius: 4px;
    }
    
    .cell-orange {
        background-color: #f39c12 !important;
        color: white;
        font-weight: bold;
        padding: 8px;
        border-radius: 4px;
    }
    
    .cell-green {
        background-color: #27ae60 !important;
        color: white;
        font-weight: bold;
        padding: 8px;
        border-radius: 4px;
    }
    
    /* Employee details panel */
    .detail-panel {
        background: #2c3e50;
        padding: 20px;
        border-radius: 8px;
        color: white;
    }
    
    .detail-header {
        background: #34495e;
        padding: 12px;
        border-radius: 6px;
        margin-bottom: 15px;
        font-weight: bold;
    }
    
    .detail-row {
        display: flex;
        justify-content: space-between;
        padding: 10px 0;
        border-bottom: 1px solid rgba(255,255,255,0.1);
    }
    
    .detail-label {
        font-weight: 500;
        opacity: 0.8;
    }
    
    .detail-value {
        font-weight: bold;
        color: #3498db;
    }
</style>
""", unsafe_allow_html=True)

# TITLE
st.markdown("<h1 style='text-align: center; color: white; background: linear-gradient(135deg, #34495e 0%, #2c3e50 100%); padding: 20px; border-radius: 10px;'>📅 Employee Attendance Dashboard</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #95a5a6; font-size: 14px; margin-top: -10px;'>Work Hours: 9:30 AM - 6:00 PM</p>", unsafe_allow_html=True)

# BUSINESS RULES (CONSTANTS)
WORK_START = time(9, 30)
WORK_END = time(18, 0)
LATE_GRACE_PERIOD = 15  # Minutes grace before marking late
FULL_DAY_HOURS = 8
STANDARD_LUNCH_DEDUCTION = 1.0  # Hours to auto-deduct if no lunch detected
LUNCH_START = time(12, 0)
LUNCH_END = time(15, 0)
MIN_GAP_FOR_LUNCH = 0.3  # Hours (20 minutes minimum to count as lunch)

# HELPER FUNCTIONS
def parse_time(time_val):
    """Convert various time formats to datetime.time"""
    if pd.isna(time_val):
        return None
    
    if isinstance(time_val, time):
        return time_val
    
    if isinstance(time_val, datetime):
        return time_val.time()
    
    if isinstance(time_val, str):
        try:
            # Try parsing common formats
            for fmt in ['%H:%M:%S', '%H:%M', '%I:%M:%S %p', '%I:%M %p']:
                try:
                    return datetime.strptime(time_val, fmt).time()
                except:
                    continue
        except:
            pass
    
    return None

def time_to_minutes(t):
    """Convert time to minutes since midnight"""
    if t is None:
        return 0
    return t.hour * 60 + t.minute

def minutes_to_hours_str(minutes):
    """Convert minutes to 'X hrs Y mins' format"""
    if pd.isna(minutes) or minutes == 0:
        return "0 hrs"
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    if mins > 0:
        return f"{hours} hrs {mins} mins"
    return f"{hours} hrs"

def process_attendance_data(df):
    """Process raw attendance data using largest-gap lunch detection logic"""
    
    # Standardize column names
    df.columns = df.columns.str.strip()
    
    # Find relevant columns
    name_col = None
    datetime_col = None
    
    for col in df.columns:
        col_lower = col.lower()
        if 'name' in col_lower and 'department' not in col_lower:
            name_col = col
        elif 'date/time' in col_lower or 'datetime' in col_lower or 'date' in col_lower:
            datetime_col = col
    
    if not name_col or not datetime_col:
        st.error("⚠️ Could not find Name and Date/Time columns")
        return None
    
    # Parse the combined Date/Time column
    df['Timestamp'] = pd.to_datetime(df[datetime_col], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['Timestamp'])
    
    # Extract date and time
    df['Date'] = df['Timestamp'].dt.date
    df['Time'] = df['Timestamp'].dt.time
    df['Employee'] = df[name_col]
    
    # Sort by employee and timestamp
    df = df.sort_values(by=['Employee', 'Timestamp'])
    
    # Process each employee-date combination
    results = []
    grouped = df.groupby(['Employee', 'Date'])
    
    for (emp, date), group in grouped:
        punches = group['Timestamp'].sort_values().tolist()
        
        if len(punches) < 2:
            continue  # Skip incomplete days
        
        first_in = punches[0]
        last_out = punches[-1]
        punch_count = len(punches)
        
        # Calculate Gross Duration (total time between first and last punch)
        gross_duration_hours = (last_out - first_in).total_seconds() / 3600
        
        # Lunch Detection Logic
        lunch_duration_hours = 0
        lunch_type = "None"
        
        if punch_count >= 4:
            # Find largest gap between consecutive punches
            gaps = []
            for i in range(len(punches) - 1):
                gap_hours = (punches[i+1] - punches[i]).total_seconds() / 3600
                gaps.append(gap_hours)
            
            if gaps:
                max_gap = max(gaps)
                if max_gap > MIN_GAP_FOR_LUNCH:  # Only count if > 20 minutes
                    lunch_duration_hours = max_gap
                    lunch_type = "Detected"
        
        elif punch_count > 1 and gross_duration_hours > 5:
            # Only 2-3 punches but long day - auto-deduct standard lunch
            lunch_duration_hours = STANDARD_LUNCH_DEDUCTION
            lunch_type = "Auto-Deducted"
        
        # Net Work Hours
        net_work_hours = max(0, gross_duration_hours - lunch_duration_hours)
        
        # Lateness Check (with grace period)
        start_threshold = pd.Timestamp(f"{date} {WORK_START.strftime('%H:%M:%S')}")
        late_threshold = start_threshold + pd.Timedelta(minutes=LATE_GRACE_PERIOD)
        
        is_late = first_in > late_threshold
        minutes_late = 0
        if is_late:
            minutes_late = (first_in - start_threshold).total_seconds() / 60
        
        # Status Determination
        is_not_full_time = net_work_hours < FULL_DAY_HOURS
        is_half_day = net_work_hours < 4
        
        # Flags for dashboard
        excess_lunch = lunch_duration_hours > 1.0  # More than 1 hour lunch
        suspicious = punch_count > 8  # Too many punches
        
        results.append({
            'Employee': emp,
            'Date': date,
            'Day': first_in.strftime('%A'),
            'FirstCheckIn': first_in.time(),
            'LastCheckOut': last_out.time(),
            'PunchCount': punch_count,
            'GrossHours': gross_duration_hours,
            'LunchDuration': lunch_duration_hours * 60,  # Convert to minutes for consistency
            'LunchType': lunch_type,
            'NetWorkHours': net_work_hours * 60,  # Convert to minutes
            'Late': is_late,
            'MinutesLate': int(minutes_late),
            'NotFullTime': is_not_full_time,
            'HalfDay': is_half_day,
            'ExcessLunch': excess_lunch,
            'Suspicious': suspicious,
            # For backwards compatibility with dashboard
            'TotalPresence': gross_duration_hours * 60,
            'BreakTime': lunch_duration_hours * 60
        })
    
    return pd.DataFrame(results)

# FILE UPLOAD
uploaded_file = st.file_uploader("📤 Upload Excel Attendance Sheet", type=['xlsx', 'xls', 'csv'])

if uploaded_file is not None:
    try:
        # Detect file type and load accordingly
        file_name = uploaded_file.name.lower()
        
        if file_name.endswith('.csv'):
            # Load CSV
            df_raw = pd.read_csv(uploaded_file)
        elif file_name.endswith('.xls'):
            # Load old Excel format (.xls) using xlrd engine
            df_raw = pd.read_excel(uploaded_file, engine='xlrd')
        elif file_name.endswith('.xlsx'):
            # Load new Excel format (.xlsx) using openpyxl engine
            df_raw = pd.read_excel(uploaded_file, engine='openpyxl')
        else:
            st.error("⚠️ Unsupported file format. Please upload .xls, .xlsx, or .csv file")
            st.stop()
        
        # Process attendance data
        df_metrics = process_attendance_data(df_raw)
        
        if df_metrics is not None and len(df_metrics) > 0:
            st.success(f"✅ Loaded {len(df_metrics)} attendance records for {df_metrics['Employee'].nunique()} employees")
            
            # Create downloadable Excel file
            output_buffer = io.BytesIO()
            
            # Prepare export dataframe with readable formatting
            export_df = df_metrics.copy()
            export_df['Date'] = pd.to_datetime(export_df['Date']).dt.strftime('%Y-%m-%d')
            export_df['FirstCheckIn'] = export_df['FirstCheckIn'].apply(lambda x: x.strftime('%H:%M:%S'))
            export_df['LastCheckOut'] = export_df['LastCheckOut'].apply(lambda x: x.strftime('%H:%M:%S'))
            export_df['GrossHours'] = export_df['GrossHours'].round(2)
            export_df['NetWorkHours'] = (export_df['NetWorkHours'] / 60).round(2)
            export_df['LunchDuration'] = (export_df['LunchDuration'] / 60).round(2)
            
            # Rename columns for clarity
            export_df = export_df[['Employee', 'Date', 'Day', 'FirstCheckIn', 'LastCheckOut', 
                                   'PunchCount', 'GrossHours', 'LunchDuration', 'LunchType', 
                                   'NetWorkHours', 'Late', 'MinutesLate', 'NotFullTime', 'HalfDay']]
            export_df.columns = ['Employee', 'Date', 'Day', 'First Punch', 'Last Punch', 
                                'Punch Count', 'Gross Hours', 'Lunch (Hrs)', 'Lunch Logic', 
                                'Net Work Hours', 'Is Late?', 'Minutes Late', 'Short Hours', 'Half Day']
            
            export_df.to_excel(output_buffer, index=False, engine='xlsxwriter')
            output_buffer.seek(0)
            
            # Download button
            st.download_button(
                label="📥 Download Processed Report (Excel)",
                data=output_buffer,
                file_name=f"Processed_Attendance_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
            # Calculate aggregated employee metrics
            employee_summary = df_metrics.groupby('Employee').agg({
                'FirstCheckIn': lambda x: pd.Series([time_to_minutes(t) for t in x]).mean(),
                'NetWorkHours': 'mean',
                'Late': 'sum',
                'NotFullTime': 'sum',
                'ExcessLunch': 'sum'
            }).reset_index()
            
            employee_summary['AvgCheckInTime'] = employee_summary['FirstCheckIn'].apply(
                lambda x: time(int(x // 60), int(x % 60)).strftime('%I:%M %p')
            )
            employee_summary['AvgWorkHours'] = employee_summary['NetWorkHours'].apply(
                lambda x: round(x / 60, 1)
            )
            employee_summary = employee_summary.rename(columns={
                'Late': 'LateDays',
                'NotFullTime': 'ShortDays',
                'ExcessLunch': 'ExcessLunchDays'
            })
            
            # SECTION 1: MANAGEMENT OVERVIEW
            st.markdown("<div class='section-header'>📊 Management Overview</div>", unsafe_allow_html=True)
            
            col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
            
            # KPI: % Late Employees
            with col1:
                total_employees = df_metrics['Employee'].nunique()
                late_employees = df_metrics[df_metrics['Late']]['Employee'].nunique()
                late_pct = int((late_employees / total_employees) * 100) if total_employees > 0 else 0
                
                st.markdown(f"""
                <div class='kpi-card kpi-red'>
                    <div class='kpi-number'>{late_pct}%</div>
                    <div class='kpi-label'>Late<br>Employees</div>
                </div>
                """, unsafe_allow_html=True)
            
            # KPI: % Not Full Time
            with col2:
                not_full_time_employees = df_metrics[df_metrics['NotFullTime']]['Employee'].nunique()
                not_full_pct = int((not_full_time_employees / total_employees) * 100) if total_employees > 0 else 0
                
                st.markdown(f"""
                <div class='kpi-card kpi-orange'>
                    <div class='kpi-number'>{not_full_pct}%</div>
                    <div class='kpi-label'>Not<br>Full Time</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Top 5 Late Comers
            with col3:
                top_late = employee_summary.nlargest(5, 'LateDays')[['Employee', 'LateDays']]
                
                late_list_html = "<div class='top-list'><div style='font-weight: bold; margin-bottom: 10px; font-size: 14px; text-align: center; border-bottom: 2px solid rgba(255,255,255,0.2); padding-bottom: 8px;'>Top 5 Late Comers</div>"
                for idx, row in top_late.iterrows():
                    late_list_html += f"<div class='top-list-item'>{row['Employee']}</div>"
                late_list_html += "</div>"
                
                st.markdown(late_list_html, unsafe_allow_html=True)
            
            # Top 5 Excess Lunch
            with col4:
                top_lunch = employee_summary.nlargest(5, 'ExcessLunchDays')[['Employee', 'ExcessLunchDays']]
                
                lunch_list_html = "<div class='top-list'><div style='font-weight: bold; margin-bottom: 10px; font-size: 14px; text-align: center; border-bottom: 2px solid rgba(255,255,255,0.2); padding-bottom: 8px;'>Top 5 Long Lunches</div>"
                for idx, row in top_lunch.iterrows():
                    lunch_list_html += f"<div class='top-list-item'>{row['Employee']}</div>"
                lunch_list_html += "</div>"
                
                st.markdown(lunch_list_html, unsafe_allow_html=True)
            
            # SECTION 2 & 3: TWO COLUMN LAYOUT
            col_table, col_detail = st.columns([2, 1])
            
            with col_table:
                # SECTION 2: EMPLOYEE COMPLIANCE SUMMARY
                st.markdown("<div class='section-header'>👥 Employee Compliance Summary</div>", unsafe_allow_html=True)
                
                # Create styled dataframe
                def color_check_in(val):
                    try:
                        t = datetime.strptime(val, '%I:%M %p').time()
                        late_cutoff = time(9, 45)  # 9:30 +  15 minutes grace
                        if t > late_cutoff:
                            return 'background-color: #e74c3c; color: white; font-weight: bold;'
                        elif t > time(9, 35):
                            return 'background-color: #f39c12; color: white; font-weight: bold;'
                        else:
                            return 'background-color: #27ae60; color: white; font-weight: bold;'
                    except:
                        return ''
                
                def color_work_hours(val):
                    if val < 7.5:
                        return 'background-color: #e74c3c; color: white; font-weight: bold;'
                    elif val < 8.0:
                        return 'background-color: #f39c12; color: white; font-weight: bold;'
                    else:
                        return 'background-color: #27ae60; color: white; font-weight: bold;'
                
                def color_count(val):
                    if val > 5:
                        return 'background-color: #e74c3c; color: white; font-weight: bold;'
                    elif val > 2:
                        return 'background-color: #f39c12; color: white; font-weight: bold;'
                    elif val == 0:
                        return 'background-color: #27ae60; color: white; font-weight: bold;'
                    else:
                        return ''
                
                display_df = employee_summary[['Employee', 'AvgCheckInTime', 'AvgWorkHours', 'LateDays', 'ShortDays', 'ExcessLunchDays']].copy()
                display_df.columns = ['Employee', 'Avg Check-In', 'Avg Work Hours', 'Late Days', 'Short Days', 'Excess Lunches']
                
                styled_df = display_df.style.applymap(color_check_in, subset=['Avg Check-In']) \
                                            .applymap(color_work_hours, subset=['Avg Work Hours']) \
                                            .applymap(color_count, subset=['Late Days', 'Short Days', 'Excess Lunches'])
                
                st.dataframe(styled_df, use_container_width=True, height=400)
            
            with col_detail:
                # SECTION 3: EMPLOYEE DRILL-DOWN
                st.markdown("<div class='section-header'>🔍 Employee Details</div>", unsafe_allow_html=True)
                
                # Employee selector
                selected_employee = st.selectbox("Select Employee:", employee_summary['Employee'].unique())
                
                # Get employee data
                emp_data = df_metrics[df_metrics['Employee'] == selected_employee].sort_values('Date', ascending=False)
                
                if len(emp_data) > 0:
                    # Today's/Latest Summary
                    latest_day = emp_data.iloc[0]
                    
                    st.markdown("<div class='detail-header'>Today's Summary</div>", unsafe_allow_html=True)
                    
                    st.markdown(f"""
                    <div class='detail-panel' style='padding: 15px;'>
                        <div class='detail-row'>
                            <span class='detail-label'>First Check-In:</span>
                            <span class='detail-value'>{latest_day['FirstCheckIn'].strftime('%I:%M %p')}</span>
                        </div>
                        <div class='detail-row'>
                            <span class='detail-label'>Last Check-Out:</span>
                            <span class='detail-value'>{latest_day['LastCheckOut'].strftime('%I:%M %p')}</span>
                        </div>
                        <div class='detail-row'>
                            <span class='detail-label'>Net Work Hours:</span>
                            <span class='detail-value'>{minutes_to_hours_str(latest_day['NetWorkHours'])}</span>
                        </div>
                        <div class='detail-row'>
                            <span class='detail-label'>Lunch Break:</span>
                            <span class='detail-value'>{minutes_to_hours_str(latest_day['LunchDuration'])}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Daily Activity Timeline
                    st.markdown("<div class='detail-header' style='margin-top: 20px;'>Daily Activity</div>", unsafe_allow_html=True)
                    
                    # Create timeline visualization
                    work_start_mins = time_to_minutes(time(9, 30))
                    work_end_mins = time_to_minutes(time(12, 0))
                    
                    first_in_mins = time_to_minutes(latest_day['FirstCheckIn'])
                    last_out_mins = time_to_minutes(latest_day['LastCheckOut'])
                    lunch_start_mins = time_to_minutes(time(12, 30))
                    lunch_end_mins = lunch_start_mins + latest_day['LunchDuration']
                    
                    fig = go.Figure()
                    
                    # Work period 1 (morning)
                    fig.add_trace(go.Bar(
                        y=['Activity'],
                        x=[lunch_start_mins - first_in_mins],
                        orientation='h',
                        marker=dict(color='#3498db'),
                        name='Work Period',
                        base=first_in_mins,
                        hovertemplate='Work<extra></extra>'
                    ))
                    
                    # Lunch break
                    if latest_day['LunchDuration'] > 0:
                        fig.add_trace(go.Bar(
                            y=['Activity'],
                            x=[latest_day['LunchDuration']],
                            orientation='h',
                            marker=dict(color='#f39c12'),
                            name='Lunch Break',
                            base=lunch_start_mins,
                            hovertemplate='Lunch<extra></extra>'
                        ))
                    
                    # Work period 2 (afternoon)
                    fig.add_trace(go.Bar(
                        y=['Activity'],
                        x=[last_out_mins - lunch_end_mins],
                        orientation='h',
                        marker=dict(color='#3498db'),
                        name='Work Period',
                        base=lunch_end_mins,
                        showlegend=False,
                        hovertemplate='Work<extra></extra>'
                    ))
                    
                    fig.update_layout(
                        barmode='overlay',
                        height=150,
                        margin=dict(l=0, r=0, t=0, b=30),
                        xaxis=dict(
                            range=[time_to_minutes(time(9, 30)), time_to_minutes(time(18, 30))],
                            tickmode='array',
                            tickvals=[570, 720, 1080],
                            ticktext=['9:30 AM', '12:00 PM', '6:00 PM'],
                            showgrid=False
                        ),
                        yaxis=dict(showticklabels=False),
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        showlegend=True,
                        legend=dict(
                            orientation='h',
                            yanchor='bottom',
                            y=-0.5,
                            xanchor='center',
                            x=0.5,
                            font=dict(size=10, color='white')
                        ),
                        font=dict(color='white')
                    )
                    
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                
        else:
            st.warning("⚠️ No valid attendance data found. Please check your file format.")
            
    except Exception as e:
        st.error(f"❌ Error processing file: {str(e)}")
        st.write("Please ensure your Excel file has the following columns:")
        st.write("- Employee Name / Employee ID")
        st.write("- Date")
        st.write("- Time")
        st.write("- Punch Type (optional)")

else:
    # Show instructions when no file is uploaded
    st.info("👆 Please upload an Excel attendance sheet to begin")
    
    st.markdown("### 📋 File Format Requirements")
    st.markdown("""
    Your Excel file should contain the following columns:
    - **Employee Name** or **Employee ID**
    - **Date** (any standard date format)
    - **Time** (HH:MM or HH:MM:SS format)
    - **Punch Type** (optional: Check-In / Check-Out)
    
    The system will automatically:
    - Handle multiple check-ins/outs per day
    - Calculate break times and lunch duration
    - Identify late arrivals and compliance violations
    - Generate comprehensive reports and dashboards
    """)
    
    # Show sample data format
    st.markdown("### 📄 Sample Data Format")
    sample_data = pd.DataFrame({
        'Employee Name': ['John Doe', 'John Doe', 'John Doe', 'John Doe', 'Jane Smith', 'Jane Smith'],
        'Date': ['2026-01-21', '2026-01-21', '2026-01-21', '2026-01-21', '2026-01-21', '2026-01-21'],
        'Time': ['09:52:00', '12:30:00', '13:45:00', '18:05:00', '09:25:00', '18:00:00'],
        'Punch Type': ['Check-In', 'Check-Out', 'Check-In', 'Check-Out', 'Check-In', 'Check-Out']
    })
    st.dataframe(sample_data, use_container_width=True)
