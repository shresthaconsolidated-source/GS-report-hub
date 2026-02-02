import streamlit as st
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Global Select Hub",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS (PREMIUM DARK THEME) ---
# --- CUSTOM CSS (NEON SPACE THEME) ---
st.markdown("""
<style>
    /* IMPORT FONTS */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        color: #e2e8f0;
    }

    /* NEBULA BACKGROUND */
    .stApp {
        background-color: #030712; /* Ink Black */
        background-image: 
            radial-gradient(at 0% 0%, rgba(56, 189, 248, 0.1) 0px, transparent 50%),
            radial-gradient(at 100% 0%, rgba(139, 92, 246, 0.1) 0px, transparent 50%),
            radial-gradient(at 100% 100%, rgba(236, 72, 153, 0.05) 0px, transparent 50%),
            radial-gradient(at 0% 100%, rgba(16, 185, 129, 0.05) 0px, transparent 50%);
        background-attachment: fixed;
    }

    /* SIDEBAR */
    section[data-testid="stSidebar"] {
        background-color: #020617; /* Darker than main */
        border-right: 1px solid #1e293b;
    }

    /* HERO SECTION REMOVED (To match screenshot minimalism, or kept minimal) */
    .hero-container {
        display: none; /* Hiding hero to match the dashboard look in screenshot which focuses on search */
    }

    /* GLASSMORMISM CARDS WITH GLOW */
    div[data-testid="stContainer"] {
        background: rgba(15, 23, 42, 0.6); /* Semi-transparent slate */
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        padding: 1.5rem;
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.05);
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
        height: 100%;
        display: flex;
        flex-direction: column;
        position: relative;
    }
    
    div[data-testid="stContainer"]:hover {
        transform: translateY(-5px);
    }

    /* SPECIFIC GLOWS (Applied via container selection hack or just general style) 
       Since we can't easily target specific streamlt containers with CSS classes from Python, 
       we'll rely on the inner HTML decoration to create the glow effect.
    */

    /* CARD CONTENT */
    .card-icon {
        font-size: 1.8rem;
        margin-bottom: 1rem;
        width: 48px;
        height: 48px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 12px;
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.05);
        color: #fff;
    }

    .card-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #fff;
        margin-bottom: 0.5rem;
        letter-spacing: 0.01em;
    }
    
    .card-desc {
        font-size: 0.85rem;
        color: #94a3b8;
        line-height: 1.5;
        flex-grow: 1;
        margin-bottom: 1.5rem;
    }

    /* CATEGORY HEADERS - NEON LINES */
    .neon-header {
        font-size: 0.8rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-top: 2.5rem;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 15px;
    }
    
    .line-hr { height: 1px; flex-grow: 1; background: linear-gradient(90deg, #10b981, transparent); box-shadow: 0 0 10px #10b981; }
    .text-hr { color: #34d399; text-shadow: 0 0 15px rgba(52, 211, 153, 0.5); }
    
    .line-sales { height: 1px; flex-grow: 1; background: linear-gradient(90deg, #3b82f6, transparent); box-shadow: 0 0 10px #3b82f6; }
    .text-sales { color: #60a5fa; text-shadow: 0 0 15px rgba(96, 165, 250, 0.5); }
    
    .line-compliance { height: 1px; flex-grow: 1; background: linear-gradient(90deg, #f43f5e, transparent); box-shadow: 0 0 10px #f43f5e; }
    .text-compliance { color: #fb7185; text-shadow: 0 0 15px rgba(251, 113, 133, 0.5); }

    /* SEARCH BAR (Glowing Pill) */
    input[type="text"] {
        background-color: rgba(15, 23, 42, 0.8) !important;
        border: 1px solid rgba(148, 163, 184, 0.2) !important;
        color: #e2e8f0 !important;
        border-radius: 9999px !important; /* Pill shape */
        padding: 12px 24px !important;
        font-size: 0.95rem;
    }
    input[type="text"]:focus {
        border-color: #6366f1 !important;
        box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.1) !important;
    }

    /* LAUNCH BUTTONS (Neon Ghost) */
    div.stButton > button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
        background: radial-gradient(circle, rgba(255,255,255,0.05) 0%, rgba(0,0,0,0) 100%);
        border: 1px solid rgba(255, 255, 255, 0.1);
        color: #cbd5e1;
        transition: all 0.3s ease;
        text-transform: uppercase;
        font-size: 0.75rem;
        letter-spacing: 1px;
    }
    div.stButton > button:hover {
        border-color: #fff;
        color: #fff;
        box-shadow: 0 0 15px rgba(255, 255, 255, 0.1);
        transform: scale(1.02);
    }

    /* HIDE CHROME */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
</style>
""", unsafe_allow_html=True)

# --- HERO SECTION (Minimal) ---
# To match screenshot, we might barely have one, or just a title.
# We'll put the Date/Status in the sidebar or very small at top.
today_str = datetime.now().strftime("%B %d, %Y")

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("""
    <div style="margin-bottom: 2rem;">
        <div style="font-weight:700; font-size:1.2rem; color:#fff; display:flex; align-items:center; gap:10px;">
            <span style="font-size:1.5rem;">🌌</span> Dashboard
        </div>
        <div style="color:#64748b; font-size:0.8rem; margin-top:5px;">Global Select Enterprise</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.caption("NAVIGATION")
    # Quick nav links could go here if we wanted to mimic the screenshot's list
    
    st.markdown("---")
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        
    st.markdown(f"""
    <div style="margin-top: auto; padding-top: 2rem; color: #475569; font-size: 0.75rem;">
        {today_str}<br>
        <span style="color:#10b981">● System Online</span>
    </div>
    """, unsafe_allow_html=True)

# --- REPORT DATA (Central Registry) ---
REPORTS = [
    {
        "title": "Visa Report",
        "icon": "📊",
        "desc": "Track weekly visa expiries. Automated filtering for Section 500/485 compliance check.",
        "category": "Compliance & Immigration",
        "category_short": "Compliance",
        "page": "pages/1_📊_Visa_Report.py"
    },
    {
        "title": "Lead Report",
        "icon": "🎯",
        "desc": "Sales funnel visualization from initial lead intake to final application submission.",
        "category": "Sales & Operations",
        "category_short": "Sales",
        "page": "pages/2_🎯_Lead_Report.py"
    },
    {
        "title": "IELTS/PTE Report",
        "icon": "📚",
        "desc": "Revenue tracking for prep classes. Distinguishes between book sales and tuition fees.",
        "category": "Sales & Operations",
        "category_short": "Sales",
        "page": "pages/3_📚_IELTS_PTE_Report.py"
    },
    {
        "title": "AU COE Report",
        "icon": "🎓",
        "desc": "Monitor Confirmation of Enrolment expiries and trigger renewal alerts.",
        "category": "Compliance & Immigration",
        "category_short": "Compliance",
        "page": "pages/4_🎓_COE_Report.py"
    },
    {
        "title": "Attendance Report",
        "icon": "📅",
        "desc": "Process biometric data logs to calculate net work hours and flag late arrivals.",
        "category": "Human Resources",
        "category_short": "HR",
        "page": "pages/5_📅_Attendance_Report.py"
    },
    {
        "title": "HR Analytics",
        "icon": "👥",
        "desc": "Live workforce demographics and compensation analysis powered by Notion data.",
        "category": "Human Resources",
        "category_short": "HR",
        "page": "pages/6_👥_HR_Analytics.py"
    },
    {
        "title": "HR Documents",
        "icon": "📝",
        "desc": "Auto-generate official salary certificates and experience letters in seconds.",
        "category": "Human Resources",
        "category_short": "HR",
        "page": "pages/7_📝_HR_Docs_Generator.py"
    },
    {
        "title": "Financial Report",
        "icon": "💰",
        "desc": "Consolidated P&L dashboard. Integrates Wise, Bank, and Cash flows.",
        "category": "Sales & Operations",
        "category_short": "Sales",
        "page": "pages/8_💰_Financial_Report.py"
    }
]

# --- SEARCH ---
# Large Centered Search
st.markdown("<br>", unsafe_allow_html=True)
col_l, col_search, col_r = st.columns([1, 6, 1])
with col_search:
    search_query = st.text_input("", placeholder="Wait... Computing... Search Modules...", label_visibility="collapsed").lower()

st.markdown("<br>", unsafe_allow_html=True)

# --- RENDER LOGIC ---
filtered_reports = [
    r for r in REPORTS 
    if search_query in r['title'].lower() 
    or search_query in r['desc'].lower()
    or search_query in r['category'].lower()
]

# Categories
categories = sorted(list(set(r['category'] for r in filtered_reports)))
PREFERRED_ORDER = ["Human Resources", "Sales & Operations", "Compliance & Immigration"]
categories = sorted(categories, key=lambda x: PREFERRED_ORDER.index(x) if x in PREFERRED_ORDER else 99)

def get_glow_style(cat):
    # Returns CSS style string for the inner div border/glow
    if "Human" in cat: 
        return "box-shadow: 0 0 20px -5px rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.3);"
    if "Sales" in cat: 
        return "box-shadow: 0 0 20px -5px rgba(59, 130, 246, 0.15); border: 1px solid rgba(59, 130, 246, 0.3);"
    if "Compliance" in cat: 
        return "box-shadow: 0 0 20px -5px rgba(244, 63, 94, 0.15); border: 1px solid rgba(244, 63, 94, 0.3);"
    return ""

def get_header_style(cat):
    if "Human" in cat: return "text-hr", "line-hr"
    if "Sales" in cat: return "text-sales", "line-sales"
    if "Compliance" in cat: return "text-compliance", "line-compliance"
    return "text-sales", "line-sales"

for cat in categories:
    # Neon Header
    text_class, line_class = get_header_style(cat)
    st.markdown(f"""
    <div class="neon-header">
        <span class="{text_class}">{cat}</span>
        <div class="{line_class}"></div>
    </div>
    """, unsafe_allow_html=True)
    
    cat_reports = [r for r in filtered_reports if r['category'] == cat]
    
    cols = st.columns(3)
    for i, report in enumerate(cat_reports):
        col = cols[i % 3]
        with col:
            with st.container():
                # We inject a div that acts as the glowing border container
                glow_style = get_glow_style(cat)
                
                # Visual Content
                st.markdown(f"""
                <div style="{glow_style} position:absolute; top:0; left:0; right:0; bottom:0; border-radius:16px; pointer-events:none;"></div>
                <div class="card-icon">{report['icon']}</div>
                <div class="card-title">{report['title']}</div>
                <div class="card-desc">{report['desc']}</div>
                """, unsafe_allow_html=True)
                
                if st.button("Launch", key=report['title'], use_container_width=True):
                    st.switch_page(report['page'])
    
    st.markdown("<br>", unsafe_allow_html=True)

# Footer
st.markdown("""
<div style="text-align: center; color: #475569; font-size: 0.8rem; margin-top: 4rem; border-top:1px solid #1e293b; padding-top:2rem;">
    &copy; 2026 Global Select &nbsp;•&nbsp; System ID: GLBL-01
</div>
""", unsafe_allow_html=True)
