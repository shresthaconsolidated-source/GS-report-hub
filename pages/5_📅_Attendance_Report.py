import streamlit as st
import pandas as pd
import json
import streamlit.components.v1 as components
from datetime import time

# PAGE SETUP
st.set_page_config(page_title="Attendance - Monthly Overview", page_icon="📅", layout="wide")

# CUSTOM CSS FOR STREAMLIT INTERFACE ONLY (e.g. File Uploader and Title)
st.markdown("""
<style>
    .main {
        background-color: #1a1f2e;
    }
    .stApp > header {
        background-color: transparent;
    }
    .stFileUploader {
        padding: 20px;
        background: rgba(255,255,255,0.05);
        border-radius: 10px;
    }
    h1 {
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# CONSTANTS
REQUIRED_HOURS = 8.0
LATE_THRESHOLD = time(9, 30)
CHRONIC_LATE_THRESHOLD = 0.20

# DATA PROCESSING FUNCTION
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
    df['Date'] = df['Timestamp'].dt.strftime('%Y-%m-%d')
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
            'FirstIn': first_in.strftime('%H:%M:%S'),
            'LastOut': last_out.strftime('%H:%M:%S'),
            'WorkHours': round(work_hours, 1),
            'IsLate': bool(is_late),
            'IsEarlyExit': bool(is_early_exit),
            'IsCompliant': bool(is_compliant),
            'Note': note
        })
    
    return pd.DataFrame(results)

# PURE HTML/JS DASHBOARD TEMPLATE
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<style>
    /* RESET & BASE STYLES */
    :root {{
        --bg-color: #1a1f2e;
        --card-bg: #2c3e50;
        --text-color: white;
        --green: #27ae60;
        --blue: #3498db;
        --red: #e74c3c;
        --orange: #f39c12;
    }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        background-color: var(--bg-color);
        color: var(--text-color);
        margin: 0;
        padding: 0;
        overflow-x: hidden;
    }}
    
    /* DASHBOARD GRID */
    .dashboard-container {{
        display: flex;
        flex-direction: column;
        gap: 20px;
        padding: 10px;
    }}
    
    /* HEADER */
    .header {{
        background: linear-gradient(135deg, #3d5a80 0%, #2c3e50 100%);
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 20px;
    }}
    .header h1 {{ margin: 0; font-size: 24px; }}
    .header p {{ margin: 5px 0 0 0; color: #bdc3c7; font-size: 14px; }}
    
    /* METRIC CARDS ROW */
    .metrics-row {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 20px;
    }}
    
    .metric-card {{
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        color: white;
        height: 120px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        position: relative;
    }}
    
    .metric-title {{ font-size: 13px; text-transform: uppercase; margin-bottom: 10px; opacity: 0.9; }}
    .metric-value {{ font-size: 42px; font-weight: bold; margin: 0; }}
    .metric-hint {{ font-size: 11px; margin-top: 5px; opacity: 0.8; font-style: italic; }}
    
    .card-green {{ background: linear-gradient(135deg, #27ae60 0%, #229954 100%); }}
    .card-blue {{ background: linear-gradient(135deg, #3498db 0%, #2980b9 100%); }}
    .card-red {{ background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%); cursor: pointer; transition: transform 0.2s; }}
    .card-orange {{ background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%); cursor: pointer; transition: transform 0.2s; }}
    
    .card-red:hover, .card-orange:hover {{ transform: scale(1.05); z-index: 10; }}

    /* MAIN CONTENT SPLIT */
    .main-content {{
        display: grid;
        grid-template-columns: 2fr 1.2fr;
        gap: 20px;
    }}
    
    /* TABLES SECTION */
    .section-header {{
        background: #2c3e50;
        padding: 10px 15px;
        border-radius: 8px 8px 0 0;
        font-weight: bold;
        border-bottom: 1px solid #34495e;
    }}
    
    .data-table-container {{
        background: #232d3f;
        border-radius: 8px;
        margin-bottom: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }}
    
    .data-row {{
        display: flex;
        justify-content: space-between;
        padding: 12px 15px;
        border-bottom: 1px solid #34495e;
        align-items: center;
    }}
    .data-row:last-child {{ border-bottom: none; }}
    
    .emp-btn {{
        background: transparent;
        border: 1px solid #3498db;
        color: #3498db;
        padding: 5px 10px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
        text-align: left;
    }}
    .emp-btn:hover {{ background: #3498db; color: white; }}
    
    .metric-small {{ font-size: 14px; font-weight: bold; }}
    .metric-label {{ font-size: 11px; color: #95a5a6; }}
    
    /* CALENDAR SECTION */
    .calendar-wrapper {{
        background: #232d3f;
        border-radius: 8px;
        padding: 15px;
    }}
    .cal-controls {{ display: flex; gap: 10px; margin-bottom: 15px; }}
    .cal-select {{ background: #34495e; color: white; border: none; padding: 5px; border-radius: 4px; flex: 1; }}
    
    .cal-grid {{
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 4px;
        margin-top: 10px;
    }}
    .cal-header {{ text-align: center; font-size: 11px; color: #95a5a6; padding-bottom: 5px; }}
    .cal-day {{
        aspect-ratio: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 12px;
        border-radius: 4px;
        background: #2c3e50;
    }}
    .day-compliant {{ background: var(--green); }}
    .day-late {{ background: var(--orange); }}
    .day-risk {{ background: var(--red); }}
    .day-empty {{ opacity: 0; }}
    
    /* MODAL OVERLAY */
    .modal-overlay {{
        display: none;
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.8);
        z-index: 1000;
        justify-content: center;
        align-items: center;
    }}
    
    .modal-content {{
        background: #1a1f2e;
        width: 80%;
        max-width: 800px;
        max-height: 80vh;
        border-radius: 12px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.5);
        display: flex;
        flex-direction: column;
        overflow: hidden;
        border: 1px solid #34495e;
    }}
    
    .modal-header {{
        padding: 15px 20px;
        background: #2c3e50;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-weight: bold;
        font-size: 18px;
    }}
    
    .close-btn {{
        background: none;
        border: none;
        color: #95a5a6;
        cursor: pointer;
        font-size: 24px;
    }}
    .close-btn:hover {{ color: white; }}
    
    .modal-body {{
        padding: 20px;
        overflow-y: auto;
    }}
    
    /* SCROLLBAR */
    ::-webkit-scrollbar {{ width: 8px; }}
    ::-webkit-scrollbar-track {{ background: #1a1f2e; }}
    ::-webkit-scrollbar-thumb {{ background: #34495e; border-radius: 4px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: #5d6d7e; }}
    
    /* HTML TABLE STYLES */
    .detail-table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 14px;
    }}
    .detail-table th {{ text-align: left; padding: 10px; border-bottom: 2px solid #34495e; color: #bdc3c7; }}
    .detail-table td {{ padding: 10px; border-bottom: 1px solid #2c3e50; }}
    .tag {{ padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; }}
    .tag-green {{ background: rgba(39, 174, 96, 0.2); color: #2ecc71; }}
    .tag-orange {{ background: rgba(243, 156, 18, 0.2); color: #f1c40f; }}
    .tag-red {{ background: rgba(231, 76, 60, 0.2); color: #e74c3c; }}

</style>
</head>
<body>

<!-- DASHBOARD CONTENT -->
<div class="dashboard-container">
    
    <!-- HEADER -->
    <div class="header">
        <h1>Monthly Management Snapshot</h1>
    </div>

    <!-- METRICS ROW -->
    <div class="metrics-row">
        <div class="metric-card card-green">
            <div class="metric-title">Avg Attendance</div>
            <div class="metric-value" id="val-attendance">--%</div>
        </div>
        <div class="metric-card card-blue">
            <div class="metric-title">Average Net Work Hrs</div>
            <div class="metric-value" id="val-hours">-- hrs</div>
        </div>
        <div class="metric-card card-red" onclick="openModal('chronic')">
            <div class="metric-title">Chronic Late</div>
            <div class="metric-value" id="val-chronic">--%</div>
            <div class="metric-hint">👆 Click for details</div>
        </div>
        <div class="metric-card card-orange" onclick="openModal('under')">
            <div class="metric-title">Under 8hrs</div>
            <div class="metric-value" id="val-under">--%</div>
            <div class="metric-hint">👆 Click for details</div>
        </div>
    </div>

    <!-- MAIN CONTENT -->
    <div class="main-content">
        
        <!-- LEFT COLUMN: LISTS -->
        <div class="left-col">
            <!-- TOP 5 COMPLIANT -->
            <div class="data-table-container">
                <div class="section-header">Top 5 Best Compliant Employees</div>
                <div id="list-compliant"></div>
            </div>

            <!-- TOP 5 RISK -->
            <div class="data-table-container">
                <div class="section-header">Top 5 Risk Employees</div>
                <div id="list-risk"></div>
            </div>
        </div>

        <!-- RIGHT COLUMN: CALENDAR -->
        <div class="right-col">
            <div class="calendar-wrapper">
                <div class="section-header" style="margin: -15px -15px 15px -15px; border-radius: 8px 8px 0 0;">Employee Calendar & Stats</div>
                
                <div class="cal-controls">
                    <select id="emp-select" class="cal-select" onchange="renderCalendar()"></select>
                </div>
                
                <!-- Weekday Headers -->
                <div class="cal-grid" style="margin-bottom: 5px;">
                    <div class="cal-header">SUN</div><div class="cal-header">MON</div>
                    <div class="cal-header">TUE</div><div class="cal-header">WED</div>
                    <div class="cal-header">THU</div><div class="cal-header">FRI</div>
                    <div class="cal-header">SAT</div>
                </div>
                
                <!-- Calendar Days -->
                <div id="calendar-grid" class="cal-grid"></div>
                
                <!-- Summary Stats -->
                <div id="emp-summary" style="margin-top: 15px; font-size: 13px;"></div>
            </div>
        </div>
    </div>

</div>

<!-- MODAL OVERLAY -->
<div id="modal" class="modal-overlay" onclick="if(event.target === this) closeModal()">
    <div class="modal-content">
        <div class="modal-header">
            <span id="modal-title">Details</span>
            <button class="close-btn" onclick="closeModal()">×</button>
        </div>
        <div class="modal-body" id="modal-body">
            <!-- Dynamic Content -->
        </div>
    </div>
</div>

<script>
    // DATA INJECTION POINT
    const stats = {STATS_JSON};
    const dailyData = {DAILY_JSON};
    
    // UTILS
    function init() {{
        updateMetrics();
        renderTopLists();
        populateEmployeeSelect();
        renderCalendar(); // Initial render for first employee
    }}

    function updateMetrics() {{
        const totalEmp = stats.length;
        if(totalEmp === 0) return;

        const avgAtt = stats.reduce((sum, s) => sum + s.AttendancePct, 0) / totalEmp;
        const avgHrs = stats.reduce((sum, s) => sum + s.AvgWorkHours, 0) / totalEmp;
        const chronicCount = stats.filter(s => s.ChronicLate).length;
        const underCount = stats.filter(s => s.UnderHours).length;

        document.getElementById('val-attendance').textContent = Math.round(avgAtt) + '%';
        document.getElementById('val-hours').textContent = avgHrs.toFixed(1) + ' hrs';
        document.getElementById('val-chronic').textContent = Math.round((chronicCount / totalEmp) * 100) + '%';
        document.getElementById('val-under').textContent = Math.round((underCount / totalEmp) * 100) + '%';
    }}

    function renderTopLists() {{
        // Top 5 Compliant
        const compliant = [...stats].sort((a,b) => b.AvgWorkHours - a.AvgWorkHours).slice(0, 5);
        const compContainer = document.getElementById('list-compliant');
        compContainer.innerHTML = compliant.map(emp => `
            <div class="data-row">
                <button class="emp-btn" onclick="openEmpDetail('${emp.Employee}')">👤 ${emp.Employee}</button>
                <div style="text-align: right;">
                    <div class="metric-small">${emp.AvgWorkHours.toFixed(1)} hrs</div>
                    <div class="metric-label">Avg Hours</div>
                </div>
                <div style="text-align: right; width: 60px;">
                    <div class="metric-small">${emp.AvgDeviation}</div>
                    <div class="metric-label">Dev</div>
                </div>
            </div>
        `).join('');

        // Top 5 Risk
        const risk = [...stats].sort((a,b) => b.TotalRiskDays - a.TotalRiskDays).slice(0, 5);
        const riskContainer = document.getElementById('list-risk');
        riskContainer.innerHTML = risk.map(emp => `
            <div class="data-row">
                <button class="emp-btn" onclick="openEmpDetail('${emp.Employee}')">⚠️ ${emp.Employee}</button>
                <div style="text-align: right;">
                    <div class="metric-small">${emp.LateDays}</div>
                    <div class="metric-label">Late</div>
                </div>
                 <div style="text-align: right;">
                    <div class="metric-small">${emp.EarlyExitDays}</div>
                    <div class="metric-label">Early</div>
                </div>
                <div style="text-align: right; width: 50px;">
                    <div class="metric-small" style="color: #e74c3c;">${emp.TotalRiskDays}</div>
                    <div class="metric-label">Risk</div>
                </div>
            </div>
        `).join('');
    }}

    function populateEmployeeSelect() {{
        const select = document.getElementById('emp-select');
        stats.sort((a,b) => a.Employee.localeCompare(b.Employee)).forEach(s => {{
            const opt = document.createElement('option');
            opt.value = s.Employee;
            opt.textContent = s.Employee;
            select.appendChild(opt);
        }});
    }}

    function renderCalendar() {{
        const empName = document.getElementById('emp-select').value;
        const container = document.getElementById('calendar-grid');
        const summaryDiv = document.getElementById('emp-summary');
        container.innerHTML = '';
        
        if(!empName) return;

        const records = dailyData.filter(d => d.Employee === empName);
        if(records.length === 0) return;

        // Determine month from first record
        const dateObj = new Date(records[0].Date);
        const year = dateObj.getFullYear();
        const month = dateObj.getMonth(); // 0-indexed
        
        // Month stats
        const empStats = stats.find(s => s.Employee === empName);
        summaryDiv.innerHTML = `
            <div style="display:flex; justify-content:space-between; border-bottom:1px solid #34495e; padding:5px 0;">
                <span>Present: <b>${empStats.PresentDays}</b></span>
                <span style="color:#f39c12">Late: <b>${empStats.LateDays}</b></span>
            </div>
            <div style="display:flex; justify-content:space-between; padding:5px 0;">
                <span style="color:#e74c3c">Early Exit: <b>${empStats.EarlyExitDays}</b></span>
                <span style="color:#3498db">Avg: <b>${empStats.AvgWorkHours.toFixed(1)}h</b></span>
            </div>
        `;

        // Generate grid
        const firstDay = new Date(year, month, 1).getDay(); // 0 = Sun
        const daysInMonth = new Date(year, month + 1, 0).getDate();

        // Empty cells for starting offset
        for(let i=0; i<firstDay; i++) {{
            container.innerHTML += '<div class="cal-day day-empty"></div>';
        }}

        // Days
        for(let d=1; d<=daysInMonth; d++) {{
            const dateStr = `${year}-${String(month+1).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
            const rec = records.find(r => r.Date === dateStr);
            
            let className = 'cal-day';
            if(rec) {{
                if(rec.IsCompliant) className += ' day-compliant';
                else if(rec.IsLate || rec.IsEarlyExit) className += ' day-late';
                else className += ' day-risk';
            }} else {{
                className += ' day-empty';
            }}

            container.innerHTML += `<div class="${className}">${rec ? d : '-'}</div>`;
        }}
    }}

    // MODAL LOGIC
    function openModal(type) {{
        const modal = document.getElementById('modal');
        const title = document.getElementById('modal-title');
        const body = document.getElementById('modal-body');
        
        modal.style.display = 'flex';
        
        if(type === 'chronic') {{
            title.textContent = '🔴 Chronic Late Employees (≥20%)';
            const data = stats.filter(s => s.ChronicLate);
            renderTable(data, ['Employee', 'LateDays', 'PresentDays'], ['Employee', 'Late Days', 'Total Days']);
        }} else if (type === 'under') {{
            title.textContent = '🟠 Employees Under 8 Hours Avg';
            const data = stats.filter(s => s.UnderHours);
            renderTable(data, ['Employee', 'AvgWorkHours', 'PresentDays'], ['Employee', 'Avg Hours', 'Days Present']);
        }}
    }}
    
    function openEmpDetail(empName) {{
        const modal = document.getElementById('modal');
        const title = document.getElementById('modal-title');
        modal.style.display = 'flex';
        title.textContent = '👤 ' + empName;
        
        const records = dailyData.filter(d => d.Employee === empName);
        renderDetailTable(records);
    }}

    function closeModal() {{
        document.getElementById('modal').style.display = 'none';
    }}

    function renderTable(data, keys, headers) {{
        const body = document.getElementById('modal-body');
        let html = '<table class="detail-table"><thead><tr>';
        headers.forEach(h => html += `<th>${h}</th>`);
        html += '</tr></thead><tbody>';
        
        data.forEach(row => {{
            html += '<tr>';
            keys.forEach(k => {{
                let val = row[k];
                if(typeof val === 'number' && !Number.isInteger(val)) val = val.toFixed(1);
                html += `<td>${val}</td>`;
            }});
            html += '</tr>';
        }});
        html += '</tbody></table>';
        body.innerHTML = html;
    }}

    function renderDetailTable(records) {{
        const body = document.getElementById('modal-body');
        let html = `<table class="detail-table">
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Entry</th>
                    <th>Exit</th>
                    <th>Hours</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>`;
            
        records.forEach(r => {{
            let tagClass = 'tag-green';
            if(r.IsLate || r.IsEarlyExit) tagClass = 'tag-orange';
            if(!r.IsCompliant && !r.IsLate && !r.IsEarlyExit) tagClass = 'tag-red';
            
            html += `<tr>
                <td>${r.Date}</td>
                <td>${r.FirstIn}</td>
                <td>${r.LastOut}</td>
                <td><strong>${r.WorkHours}</strong></td>
                <td><span class="tag ${tagClass}">${r.Note}</span></td>
            </tr>`;
        }});
        
        html += '</tbody></table>';
        body.innerHTML = html;
    }}

    // Init
    init();

</script>
</body>
</html>
"""

# MAIN APP LOGIC
st.markdown("<div class='page-title'>📅 Attendance Report (Interactive)</div>", unsafe_allow_html=True)

uploaded_file = st.file_uploader("Upload Excel Attendance Sheet", type=['xlsx', 'xls', 'csv'])

if uploaded_file is not None:
    try:
        file_name = uploaded_file.name.lower()
        if file_name.endswith('.csv'):
            df_raw = pd.read_csv(uploaded_file)
        elif file_name.endswith('.xls'):
            df_raw = pd.read_excel(uploaded_file, engine='xlrd')
        elif file_name.endswith('.xlsx'):
            df_raw = pd.read_excel(uploaded_file, engine='openpyxl')
            
        df_daily = process_attendance_simple(df_raw)
        
        if df_daily is not None and not df_daily.empty:
            
            # 1. PROCESS STATS IN PYTHON
            dates = pd.to_datetime(df_daily['Date'])
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
            
            # 2. CONVERT TO JSON FOR JS
            stats_json = employee_stats.to_json(orient="records")
            daily_json = df_daily.to_json(orient="records")
            
            # 3. INJECT HTML
            final_html = HTML_TEMPLATE.replace("{STATS_JSON}", stats_json).replace("{DAILY_JSON}", daily_json)
            
            components.html(final_html, height=800, scrolling=True)
            
        else:
            st.error("Processing failed or no data found.")
            
    except Exception as e:
        st.error(f"Error: {e}")
