import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Report Automator Hub",
    page_icon="🏠",
    layout="wide"
)

# Custom CSS for better card styling
st.markdown("""
<style>
    div[data-testid="stContainer"] {
        background-color: #262730;
        padding: 20px;
        border-radius: 10px;
        transition: transform 0.2s;
        border: 1px solid #464b5c;
    }
    div[data-testid="stContainer"]:hover {
        border-color: #ff4b4b;
    }
    .report-title {
        font-size: 1.2rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    .report-desc {
        font-size: 0.9rem;
        color: #bfc5d3;
        margin-bottom: 1rem;
        min-height: 40px;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.title("🏠 Report Automator Hub")
st.write("Centralized dashboard for all your automated reports.")

st.divider()

# --- REPORT CONFIGURATION ---
# Define all reports here. Add new ones to this list.
REPORTS = [
    {
        "title": "Visa Report",
        "icon": "📊",
        "desc": "Weekly visa expiry reports with automated filtering (SC 500/485).",
        "category": "Compliance & Immigration",
        "page": "pages/1_📊_Visa_Report.py",
        "features": ["Upload CSV/Excel", "3-month expiry filter", "Email Delivery"]
    },
    {
        "title": "AU COE Report",
        "icon": "🎓",
        "desc": "Track Australian student COE expiries and generate renewal alerts.",
        "category": "Compliance & Immigration",
        "page": "pages/4_🎓_COE_Report.py",
        "features": ["Upload Data", "< 6 Month Filter", "Email Alerts"]
    },
    {
        "title": "Lead Report",
        "icon": "🎯",
        "desc": "Track leads and completed applications with advanced filtering.",
        "category": "Sales & Operations",
        "page": "pages/2_🎯_Lead_Report.py",
        "features": ["Lead Summary", "Application Tracking", "Date Filtering"]
    },
    {
        "title": "IELTS/PTE Report",
        "icon": "📚",
        "desc": "Intelligent payment tracking, revenue analytics, and smart categorization.",
        "category": "Sales & Operations",
        "page": "pages/3_📚_IELTS_PTE_Report.py",
        "features": ["Google Sheets Sync", "Revenue Charts", "Outstanding Balance"]
    },
    {
        "title": "Attendance Report",
        "icon": "📅",
        "desc": "Employee attendance processing, work hours computation and compliance flags.",
        "category": "Human Resources",
        "page": "pages/5_📅_Attendance_Report.py",
        "features": ["Excel Upload", "Late Tracking", "Compliance Dashboard"]
    },
    {
        "title": "HR Analytics",
        "icon": "👥",
        "desc": "Live Employee Analytics Dashboard (Notion + Cloudflare + FX).",
        "category": "Human Resources",
        "page": "pages/6_👥_HR_Analytics.py",
        "features": ["Live Data", "Tenure & Demographics", "Compensation & FX"]
    }
]

# --- SEARCH & FILTER ---
col_search, col_stats = st.columns([3, 1])
with col_search:
    search_query = st.text_input("🔍 Search reports...", placeholder="Type 'Visa', 'Finance', etc.").lower()

# Filter logic
filtered_reports = [
    r for r in REPORTS 
    if search_query in r['title'].lower() 
    or search_query in r['desc'].lower()
    or search_query in r['category'].lower()
]

with col_stats:
    st.info(f"Showing **{len(filtered_reports)}** / {len(REPORTS)} reports")

# --- DISPLAY LOOP ---
# Get unique categories present in filtered results
categories = sorted(list(set(r['category'] for r in filtered_reports)))

# Order preference: HR -> Sales -> Compliance (or alphabetical)
# Let's keep a fixed order for consistency if they exist
PREFERRED_ORDER = ["Human Resources", "Sales & Operations", "Compliance & Immigration"]
categories = sorted(categories, key=lambda x: PREFERRED_ORDER.index(x) if x in PREFERRED_ORDER else 99)

if not filtered_reports:
    st.warning("No reports found matching your search.")

for cat in categories:
    st.subheader(f"📂 {cat}")
    
    # Get reports in this category
    cat_reports = [r for r in filtered_reports if r['category'] == cat]
    
    # Create grid (3 columns)
    cols = st.columns(3)
    
    for i, report in enumerate(cat_reports):
        col = cols[i % 3] # Cycle through columns
        
        with col:
            # Create a card-like container
            with st.container():
                st.markdown(f'<div class="report-title">{report["icon"]} {report["title"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="report-desc">{report["desc"]}</div>', unsafe_allow_html=True)
                
                # Feature tags (compact)
                st.caption(" • ".join(report['features'][:3]))
                
                # Action Button
                if st.button(f"Open {report['title']}", key=f"btn_{report['title']}", use_container_width=True, type="primary"):
                    st.switch_page(report['page'])
            
            st.write("") # Spacer

st.divider()
st.caption("Need a new report? Contact the development team.")
