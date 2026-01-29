import streamlit as st
import streamlit.components.v1 as components
import os

# Page configuration
st.set_page_config(
    page_title="HR Analytics Dashboard",
    page_icon="👥",
    layout="wide"
)

# Header
st.title("👥 HR Analytics Dashboard")
st.write("Premium Glass Neon Edition · Live Notion + Cloudflare + FX")

st.divider()

# Load and display the HTML dashboard
html_file_path = os.path.join(os.path.dirname(__file__), "..", "hr_analytics_dashboard.html")

try:
    with open(html_file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Display the HTML dashboard in an iframe
    components.html(html_content, height=1200, scrolling=True)
    
except FileNotFoundError:
    st.error("❌ HR Analytics Dashboard HTML file not found!")
    st.info("Please ensure 'hr_analytics_dashboard.html' is in the root directory.")
except Exception as e:
    st.error(f"❌ Error loading dashboard: {str(e)}")

st.divider()

# Info section
with st.expander("ℹ️ About HR Analytics Dashboard"):
    st.markdown("""
    ## Features
    
    ✨ **Premium Design**
    - Glass-morphism UI with neon accents
    - Smooth animations and transitions
    - Dark theme optimized for extended viewing
    
    📊 **Analytics & Insights**
    - Real-time KPI cards (Total, Active, Inactive, On Probation)
    - Employee tenure breakdown with visual charts
    - Department distribution analysis
    - Gender and age group demographics
    - Probation ending alerts
    
    👤 **Employee Detail Modal**
    - **Click on any employee card or table row** to view full details
    - Comprehensive employee information
    - Smooth popup animations
    
    💰 **Compensation Analytics**
    - Total payroll calculations in NPR
    - Average salary metrics
    - Currency-wise breakdowns with FX rates
    - Country-wise payroll distribution
    
    🔍 **Advanced Filtering**
    - Search by name, ID, or designation
    - Filter by status, department, and country
    - Real-time filter updates
    
    ## How to Use
    
    1. **View Employee Details**: Click on any employee row in the People tab
    2. **Navigate Tabs**: Switch between Overview, People, and Compensation
    3. **Quick Filters**: Click on KPI cards at the top to filter employees
    4. **Search**: Type in the search box for instant results
    
    ## Data Source
    
    Connected to Cloudflare Worker API:
    - Live data from Notion database
    - Real-time FX rate conversions
    - Automatic updates
    """)
