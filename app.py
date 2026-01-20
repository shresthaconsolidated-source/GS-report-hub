import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Report Automator Hub",
    page_icon="🏠",
    layout="wide"
)

# Header
st.title("🏠 Report Automator Hub")
st.write("Choose a report type to get started:")

st.divider()

# Create three columns for the report options
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.header("📊 Visa Report")
    st.write("Generate weekly visa expiry reports with automated filtering and email delivery.")
    st.write("**Features:**")
    st.markdown("""
    - Upload CSV/Excel files
    - Filter visas expiring in 3 months
    - Separate SC 500 and SC 485 visas
    - Generate Excel report
    - Send via email
    """)
    if st.button("📊 Open Visa Report Automator", use_container_width=True, type="primary"):
        st.switch_page("pages/1_📊_Visa_Report.py")

with col2:
    st.header("🎯 Lead Report")
    st.write("Generate weekly lead reports (Coming Soon)")
    st.write("**Features:**")
    st.markdown("""
    - Lead tracking
    - Performance metrics
    - Automated reporting
    - Email delivery
    """)
    if st.button("🎯 Open Lead Report Automator", use_container_width=True, disabled=False):
        st.switch_page("pages/2_🎯_Lead_Report.py")

with col3:
    st.header("📚 IELTS/PTE Report")
    st.write("Intelligent payment tracking and analytics")
    st.write("**Features:**")
    st.markdown("""
    - Auto-fetch from Google Sheets
    - Smart payment categorization
    - Outstanding balance tracking
    - Revenue analytics & charts
    - HTML email with embedded tables
    """)
    if st.button("📚 Open IELTS/PTE Report", use_container_width=True, type="primary"):
        st.switch_page("pages/3_📚_IELTS_PTE_Report.py")

with col4:
    st.header("🎓 COE Report")
    st.write("Track student COE expiries")
    st.write("**Features:**")
    st.markdown("""
    - Upload CSV/Excel files
    - Filter expiring COEs (< 6 months)
    - Generate Excel report
    - Automated email notification
    """)
    if st.button("🎓 Open COE Report", use_container_width=True, type="primary"):
        st.switch_page("pages/4_🎓_COE_Report.py")

st.divider()

st.caption("Select a report type above to continue")
