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
EXIT_THRESHOLD = time(18, 0)
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
        
        # LOGIC UPDATES
        is_late = first_in.time() > LATE_THRESHOLD
        
        # Strict Early Exit: Only if they left before 18:00
        is_early_exit = last_out.time() < EXIT_THRESHOLD
        
        # Compliant: Must work >=8 hours AND not be late
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
            note = "Compliant" # Case: On time, stayed late, but < 8hrs (unlikely but possible if long break logic existed, basically irrelevant here) -> actually if < 8 hours but not early exit? 
            # If came at 9:00, left at 18:00 -> 9 hours. Compliant.
            # If came at 10:30 (Late), left at 18:30 -> 8 hours. IsLate=True. Not Compliant. Note="Late Entry".
            
            # What if came 9:00, left 17:00? Early Exit = True.
            
            # Simple fallback
            if work_hours < REQUIRED_HOURS and not is_late and not is_early_exit:
                 # Came on time, left after 6, but somehow < 8 hours? (Maybe math error or same punch)
                 pass

        
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
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
    /* RESET & BASE STYLES */
    :root {
        --bg-color: #1a1f2e;
        --card-bg: #232d3f;
        --text-color: #ffffff;
        --text-muted: #95a5a6;
        --green: #27ae60;
        --blue: #2980b9;
        --red: #c0392b; 
        --orange: #d35400;
        --border-color: #34495e;
    }
    
    * { box-sizing: border-box; }

    body {
        font-family: 'Inter', sans-serif;
        background-color: var(--bg-color);
        color: var(--text-color);
        margin: 0;
        padding: 20px;
        overflow-x: hidden;
    }
    
    /* DASHBOARD GRID */
    .dashboard-container {
        display: flex;
        flex-direction: column;
        gap: 20px;
        max-width: 1400px;
        margin: 0 auto;
    }
    
    /* HEADER */
    .header {
        background: linear-gradient(90deg, #2c3e50 0%, #3d5a80 100%);
        padding: 15px 20px;
        border-radius: 6px;
        margin-bottom: 10px;
        border-bottom: 2px solid #3498db;
    }
    .header h1 { margin: 0; font-size: 20px; font-weight: 600; letter-spacing: 0.5px; }
    
    /* METRIC CARDS ROW */
    .metrics-row {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 15px;
    }
    
    .metric-card {
        border-radius: 6px;
        padding: 15px;
        text-align: center;
        color: white;
        height: 110px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        position: relative;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    }
    
    .metric-title { 
        font-size: 12px; 
        text-transform: uppercase; 
        margin-bottom: 8px; 
        font-weight: 600; 
        opacity: 0.9; 
        letter-spacing: 0.5px;
    }
    .metric-value { font-size: 38px; font-weight: 700; margin: 0; line-height: 1; }
    .metric-hint { 
        font-size: 10px; 
        margin-top: 8px; 
        opacity: 0.8; 
        font-weight: 500;
        background: rgba(0,0,0,0.1); 
        padding: 2px 8px; 
        border-radius: 10px; 
    }
    
    .card-green { background: #27ae60; }
    .card-blue { background: #2980b9; }
    .card-red { background: #c0392b; cursor: pointer; transition: transform 0.2s, box-shadow 0.2s; }
    .card-orange { background: #f39c12; cursor: pointer; transition: transform 0.2s, box-shadow 0.2s; }
    
    .card-red:hover, .card-orange:hover { transform: translateY(-2px); box-shadow: 0 6px 12px rgba(0,0,0,0.3); }

    /* MAIN CONTENT SPLIT */
    .main-content {
        display: grid;
        grid-template-columns: 1.2fr 1.2fr 1fr; /* 3 Columns */
        gap: 15px;
    }
    
    /* SECTION CONTAINERS */
    .section-container {
        background: var(--card-bg);
        border-radius: 6px;
        overflow: hidden;
        border: 1px solid var(--border-color);
        display: flex;
        flex-direction: column;
    }

    .col-left {
        /* This column will hold multiple containers */
        background: transparent; 
        border: none;
        overflow: visible;
        gap: 15px;
        display: flex;
        flex-direction: column;
    }
    
    .section-header {
        background: #34495e;
        padding: 12px 15px;
        font-size: 14px;
        font-weight: 600;
        color: white;
        border-bottom: 1px solid #2c3e50;
    }
    
    /* TABLES */
    .data-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
    }
    
    .data-table th {
        text-align: left;
        padding: 10px 15px;
        background: rgba(255,255,255,0.03);
        color: var(--text-muted);
        font-weight: 500;
        border-bottom: 1px solid var(--border-color);
        font-size: 11px;
        text-transform: uppercase;
    }
    
    .data-table td {
        padding: 10px 15px;
        border-bottom: 1px solid rgba(255,255,255,0.05);
        color: #e0e0e0;
    }
    
    .data-table tr:last-child td { border-bottom: none; }
    
    .emp-name {
        font-weight: 500;
        color: #ecf0f1;
        cursor: pointer;
        transition: color 0.2s;
        text-decoration: none;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .emp-name:hover { color: #3498db; text-decoration: underline; }
    
    /* CALENDAR SECTION */
    .calendar-body { padding: 15px; }
    
    .cal-controls { margin-bottom: 15px; }
    .cal-select { 
        width: 100%; 
        background: #1a1f2e; 
        color: white; 
        border: 1px solid var(--border-color); 
        padding: 8px; 
        border-radius: 4px;
        outline: none;
        font-family: inherit;
    }
    
    .cal-grid {
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 4px;
    }
    .cal-header { 
        text-align: center; 
        font-size: 10px; 
        color: var(--text-muted); 
        padding-bottom: 5px; 
        font-weight: 600;
    }
    .cal-day {
        aspect-ratio: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 12px;
        border-radius: 3px;
        background: #34495e;
        color: #bdc3c7;
    }
    .day-compliant { background: var(--green); color: white; }
    .day-late { background: #f39c12; color: white; }
    .day-risk { background: #e74c3c; color: white; }
    .day-empty { background: transparent; }
    .day-neutral { background: #2c3e50; color: #5d6d7e; opacity: 0.5; }
    
    /* SUMMARY STATS BELOW CALENDAR */
    .summary-stats {
        margin-top: 15px;
        background: rgba(0,0,0,0.2);
        padding: 10px;
        border-radius: 4px;
        font-size: 12px;
    }
    .stat-row { display: flex; justify-content: space-between; margin-bottom: 5px; }
    .stat-row:last-child { margin-bottom: 0; }
    
    /* MODAL */
    .modal-overlay {
        display: none;
        position: fixed;
        top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0,0,0,0.7);
        backdrop-filter: blur(2px);
        z-index: 1000;
        justify-content: center;
        align-items: center;
    }
    
    .modal-content {
        background: #232d3f;
        width: 90%;
        max-width: 800px;
        max-height: 85vh;
        border-radius: 8px;
        box-shadow: 0 15px 30px rgba(0,0,0,0.5);
        display: flex;
        flex-direction: column;
        border: 1px solid var(--border-color);
        animation: fadeIn 0.2s ease-out;
    }
    
    @keyframes fadeIn { from { opacity: 0; transform: scale(0.95); } to { opacity: 1; transform: scale(1); } }
    
    .modal-header {
        padding: 15px 20px;
        background: #2c3e50;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-weight: 600;
        font-size: 16px;
        border-bottom: 1px solid var(--border-color);
    }
    
    .close-btn {
        background: none;
        border: none;
        color: var(--text-muted);
        cursor: pointer;
        font-size: 20px;
        padding: 0 5px;
    }
    .close-btn:hover { color: white; }
    
    .modal-body {
        padding: 0;
        overflow-y: auto;
    }
    
    .detail-table { width: 100%; border-collapse: collapse; font-size: 13px; }
    .detail-table th { 
        position: sticky; top: 0; 
        background: #232d3f; 
        padding: 12px 20px; 
        text-align: left; 
        border-bottom: 2px solid var(--border-color); 
        color: var(--text-muted);
        font-size: 11px;
        text-transform: uppercase;
    }
    .detail-table td { padding: 12px 20px; border-bottom: 1px solid rgba(255,255,255,0.05); }
    .detail-table tr:hover { background: rgba(255,255,255,0.02); }

    /* TAGS */
    .status-badge { padding: 3px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; white-space: nowrap; }
    .badge-green { background: rgba(39, 174, 96, 0.2); color: #2ecc71; border: 1px solid rgba(39, 174, 96, 0.3); }
    .badge-orange { background: rgba(243, 156, 18, 0.2); color: #f1c40f; border: 1px solid rgba(243, 156, 18, 0.3); }
    .badge-red { background: rgba(231, 76, 60, 0.2); color: #e74c3c; border: 1px solid rgba(231, 76, 60, 0.3); }

    /* LAYOUT TWEAKS FOR 3-COL */
    .col-mid { grid-column: span 1; }
    .col-right { grid-column: span 1; }

</style>
</head>
<body>

<!-- DASHBOARD CONTENT -->
<div class="dashboard-container">
    
    <!-- HEADER -->
    <div class="header">
        <h1>Monthly Management Snapshot</h1>
    </div>

    <!-- METRICS -->
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

    <!-- MAIN GRID 3 COLUMNS -->
    <div class="main-content">
        
        <!-- COL 1 (LEFT): STACKED COMPLIANT + LATE -->
        <div class="col-left">
            
            <!-- TOP 5 COMPLIANT -->
            <div class="section-container">
                <div class="section-header">Top 5 Best Compliant Employees</div>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Employee</th>
                            <th style="text-align:center;">Avg Hrs</th>
                            <th style="text-align:center;">Days</th>
                        </tr>
                    </thead>
                    <tbody id="list-compliant"></tbody>
                </table>
            </div>

            <!-- TOP 5 LATE (NEW) -->
            <div class="section-container">
                <div class="section-header">Top 5 Late Employees</div>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Employee</th>
                            <th style="text-align:center;">Late</th>
                            <th style="text-align:center;">Risk</th>
                        </tr>
                    </thead>
                    <tbody id="list-late"></tbody>
                </table>
            </div>

        </div>

        <!-- COL 2: TOP 10 RISK -->
        <div class="section-container col-mid">
            <div class="section-header">Top 10 Risk Employees</div>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Employee</th>
                        <th style="text-align:center;">Late</th>
                        <th style="text-align:center;">Early</th>
                        <th style="text-align:center;">Risk</th>
                    </tr>
                </thead>
                <tbody id="list-risk"></tbody>
            </table>
        </div>

        <!-- COL 3: CALENDAR -->
        <div class="section-container col-right">
            <div class="section-header">Employee Calendar & Stats</div>
            <div class="calendar-body">
                <div class="cal-controls">
                    <select id="emp-select" class="cal-select" onchange="renderCalendar()"></select>
                </div>
                
                <div class="cal-grid" style="margin-bottom: 5px;">
                    <div class="cal-header">S</div><div class="cal-header">M</div>
                    <div class="cal-header">T</div><div class="cal-header">W</div>
                    <div class="cal-header">T</div><div class="cal-header">F</div>
                    <div class="cal-header">S</div>
                </div>
                
                <div id="calendar-grid" class="cal-grid"></div>
                
                <div id="emp-summary" class="summary-stats"></div>
            </div>
        </div>

    </div>
</div>

<!-- MODAL -->
<div id="modal" class="modal-overlay" onclick="handleOverlayClick(event)">
    <div class="modal-content">
        <div class="modal-header">
            <span id="modal-title">Details</span>
            <button class="close-btn" onclick="closeModal()">×</button>
        </div>
        <div class="modal-body" id="modal-body"></div>
    </div>
</div>

<script>
    const stats = {STATS_JSON};
    const dailyData = {DAILY_JSON};
    
    function init() {
        updateMetrics();
        renderTopLists();
        populateEmployeeSelect();
        renderCalendar();
    }

    function updateMetrics() {
        if(stats.length === 0) return;
        const avgAtt = stats.reduce((sum, s) => sum + s.AttendancePct, 0) / stats.length;
        const avgHrs = stats.reduce((sum, s) => sum + s.AvgWorkHours, 0) / stats.length;
        const chronic = stats.filter(s => s.ChronicLate).length;
        const under = stats.filter(s => s.UnderHours).length;

        setText('val-attendance', Math.round(avgAtt) + '%');
        setText('val-hours', avgHrs.toFixed(1) + ' hrs');
        setText('val-chronic', Math.round((chronic / stats.length) * 100) + '%');
        setText('val-under', Math.round((under / stats.length) * 100) + '%');
    }

    function renderTopLists() {
        // Compliant List: Sort by CompliantDays desc, then AvgHours desc
        // This ensures the "Best" are those who are actually compliant most often.
        const compliant = [...stats].sort((a,b) => {
            if (b.CompliantDays !== a.CompliantDays) return b.CompliantDays - a.CompliantDays;
            return b.AvgWorkHours - a.AvgWorkHours;
        }).slice(0, 5);
        
        document.getElementById('list-compliant').innerHTML = compliant.map(emp => `
            <tr>
                <td><div class="emp-name" onclick="openEmpDetail('${emp.Employee}')">👤 ${emp.Employee}</div></td>
                <td style="text-align:center; font-weight:600; color:#2ecc71;">${emp.AvgWorkHours.toFixed(1)}</td>
                <td style="text-align:center; color:#95a5a6;">${emp.CompliantDays}</td>
            </tr>
        `).join('');

        // Late List (NEW): Sort by LateDays desc
        const late = [...stats].sort((a,b) => b.LateDays - a.LateDays).slice(0, 5);
        document.getElementById('list-late').innerHTML = late.map(emp => `
            <tr>
                <td><div class="emp-name" onclick="openEmpDetail('${emp.Employee}')">🕒 ${emp.Employee}</div></td>
                <td style="text-align:center; color:#f39c12; font-weight:bold;">${emp.LateDays}</td>
                <td style="text-align:center;">${emp.TotalRiskDays}</td>
            </tr>
        `).join('');

        // Risk List
        const risk = [...stats].sort((a,b) => b.TotalRiskDays - a.TotalRiskDays).slice(0, 10);
        document.getElementById('list-risk').innerHTML = risk.map(emp => `
            <tr>
                <td><div class="emp-name" onclick="openEmpDetail('${emp.Employee}')">⚠️ ${emp.Employee}</div></td>
                <td style="text-align:center;">${emp.LateDays}</td>
                <td style="text-align:center;">${emp.EarlyExitDays}</td>
                <td style="text-align:center; font-weight:bold; color:#e74c3c;">${emp.TotalRiskDays}</td>
            </tr>
        `).join('');
    }

    function populateEmployeeSelect() {
        const select = document.getElementById('emp-select');
        stats.sort((a,b) => a.Employee.localeCompare(b.Employee)).forEach(s => {
            const opt = document.createElement('option');
            opt.value = s.Employee;
            opt.textContent = s.Employee;
            select.appendChild(opt);
        });
    }

    function renderCalendar() {
        const empName = document.getElementById('emp-select').value;
        const container = document.getElementById('calendar-grid');
        const summary = document.getElementById('emp-summary');
        container.innerHTML = '';
        
        if(!empName) return;

        const records = dailyData.filter(d => d.Employee === empName);
        
        // Find date range
        let year, month, daysInMonth, firstDay;
        
        if (records.length > 0) {
            const dateObj = new Date(records[0].Date);
            year = dateObj.getFullYear();
            month = dateObj.getMonth();
            firstDay = new Date(year, month, 1).getDay();
            daysInMonth = new Date(year, month + 1, 0).getDate();
        } else {
            const today = new Date();
            year = today.getFullYear();
            month = today.getMonth();
            firstDay = new Date(year, month, 1).getDay();
            daysInMonth = new Date(year, month + 1, 0).getDate();
        }
        
        const empStats = stats.find(s => s.Employee === empName);
        summary.innerHTML = `
            <div class="stat-row"><span>Present:</span> <b>${empStats.PresentDays}</b></div>
            <div class="stat-row"><span>Late:</span> <b style="color:#f39c12">${empStats.LateDays}</b></div>
            <div class="stat-row"><span>Early Exit:</span> <b style="color:#e74c3c">${empStats.EarlyExitDays}</b></div>
            <div class="stat-row"><span>Avg Hours:</span> <b style="color:#3498db">${empStats.AvgWorkHours.toFixed(1)}</b></div>
        `;

        for(let i=0; i<firstDay; i++) container.insertAdjacentHTML('beforeend', '<div class="cal-day day-empty"></div>');

        for(let d=1; d<=daysInMonth; d++) {
            const dateStr = `${year}-${String(month+1).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
            const rec = records.find(r => r.Date === dateStr);
            let cls = 'cal-day';
            
            if(rec) {
                if(rec.IsCompliant) cls += ' day-compliant';
                else if(rec.IsLate || rec.IsEarlyExit) cls += ' day-late';
                else cls += ' day-risk';
            } else {
                 cls += ' day-neutral'; 
            }
            container.insertAdjacentHTML('beforeend', `<div class="${cls}">${d}</div>`);
        }
    }

    function openModal(type) {
        showModal();
        const title = document.getElementById('modal-title');
        if(type === 'chronic') {
            title.textContent = '🔴 Chronic Late Employees (≥20%)';
            renderTable(stats.filter(s => s.ChronicLate), 
                ['Employee', 'LateDays', 'PresentDays'], 
                ['Employee', 'Late Days', 'Days Present']);
        } else if(type === 'under') {
            title.textContent = '🟠 Employees Under 8 Hours Avg';
            renderTable(stats.filter(s => s.UnderHours), 
                ['Employee', 'AvgWorkHours', 'PresentDays'], 
                ['Employee', 'Avg Hours', 'Days Present']);
        }
    }

    function openEmpDetail(empName) {
        showModal();
        document.getElementById('modal-title').textContent = '👤 ' + empName;
        renderDetailTable(dailyData.filter(d => d.Employee === empName));
    }

    function renderTable(data, keys, headers) {
        let hHtml = ''; headers.forEach(h => hHtml += `<th>${h}</th>`);
        let bHtml = '';
        data.forEach(row => {
            bHtml += '<tr>';
            keys.forEach(k => bHtml += `<td>${typeof row[k] === 'number' && !Number.isInteger(row[k]) ? row[k].toFixed(1) : row[k]}</td>`);
            bHtml += '</tr>';
        });
        document.getElementById('modal-body').innerHTML = `<table class="detail-table"><thead><tr>${hHtml}</tr></thead><tbody>${bHtml}</tbody></table>`;
    }

    function renderDetailTable(records) {
        let html = '';
        records.forEach(r => {
            let badge = 'badge-green';
            if(r.IsLate || r.IsEarlyExit) badge = 'badge-orange';
            if(!r.IsCompliant && !r.IsLate && !r.IsEarlyExit) badge = 'badge-red';
            
            html += `<tr>
                <td>${r.Date}</td>
                <td>${r.FirstIn}</td>
                <td>${r.LastOut}</td>
                <td><strong>${r.WorkHours}</strong></td>
                <td><span class="status-badge ${badge}">${r.Note}</span></td>
            </tr>`;
        });
        document.getElementById('modal-body').innerHTML = `
            <table class="detail-table">
                <thead><tr><th>Date</th><th>Entry</th><th>Exit</th><th>Hours</th><th>Status</th></tr></thead>
                <tbody>${html}</tbody>
            </table>`;
    }

    function showModal() { document.getElementById('modal').style.display = 'flex'; }
    function closeModal() { document.getElementById('modal').style.display = 'none'; }
    function handleOverlayClick(e) { if(e.target.id === 'modal') closeModal(); }
    function setText(id, txt) { document.getElementById(id).textContent = txt; }

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
            
            components.html(final_html, height=1000, scrolling=True) # Increased height for taller stacked column
            
        else:
            st.error("Processing failed or no data found.")
            
    except Exception as e:
        st.error(f"Error: {e}")
