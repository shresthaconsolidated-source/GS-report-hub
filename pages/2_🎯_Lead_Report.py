import streamlit as st
import pandas as pd
from datetime import datetime
import io

# 1. PAGE SETUP
st.set_page_config(page_title="Lead Report Automator", page_icon="🎯", layout="wide")
st.title("🎯 Lead Report Automator")
st.write("Upload your lead data file to generate automated reports.")

# Helper function to load data
def load_data(file):
    if file.name.endswith('.csv'):
        df = pd.read_csv(file)
        if "Unnamed" in str(df.columns[0]):
            file.seek(0)
            df = pd.read_csv(file, header=1)
    else:
        df_test = pd.read_excel(file, engine='openpyxl', nrows=2)
        if df_test.columns[0] == 'Unnamed: 0' or pd.isna(df_test.columns[0]):
            file.seek(0)
            df = pd.read_excel(file, engine='openpyxl', header=1)
        else:
            file.seek(0)
            df = pd.read_excel(file, engine='openpyxl', header=0)
    
    # Remove unnamed columns
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    return df

def process_application_report(df):
    try:
        # Standardize columns
        df.columns = df.columns.str.strip()
        
        # Check required columns
        required_cols = ['Status', 'Workflow Name', 'Application Owner', 'Internal Client ID']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            st.error(f"Missing columns: {', '.join(missing_cols)}")
            return None

        # Filter: Status == "In Progress"
        df_filtered = df[df['Status'] == 'In Progress'].copy()
        
        # Categorize Application Type
        def get_app_type(workflow_name):
            if pd.isna(workflow_name):
                return "Admission"
            name_lower = str(workflow_name).lower()
            if any(x in name_lower for x in ["migration service", "skills assessment", "state government"]):
                return "Migration"
            return "Admission"

        df_filtered['App_Type'] = df_filtered['Workflow Name'].apply(get_app_type)

        # Aggregation
        # 1. Distinct Count of Internal Client ID
        # 2. Count of Internal Client ID (Total Applications)
        # 3. Count of Migration Apps
        # 4. Count of Admission Apps
        
        summary = df_filtered.groupby('Application Owner').agg(
            Distinct_Clients=('Internal Client ID', 'nunique'),
            Total_Applications=('Internal Client ID', 'count'),
            Migration_Count=('App_Type', lambda x: (x == 'Migration').sum()),
            Admission_Count=('App_Type', lambda x: (x == 'Admission').sum())
        ).reset_index()
        
        # Add Grand Total Row
        total_row = pd.DataFrame({
            'Application Owner': ['Grand Total'],
            'Distinct_Clients': [df_filtered['Internal Client ID'].nunique()],
            'Total_Applications': [len(df_filtered)],
            'Migration_Count': [(df_filtered['App_Type'] == 'Migration').sum()],
            'Admission_Count': [(df_filtered['App_Type'] == 'Admission').sum()]
        })
        
        summary = pd.concat([summary, total_row], ignore_index=True)
        
        return summary

    except Exception as e:
        st.error(f"Error processing report: {e}")
        return None

col1, col2 = st.columns(2)

with col1:
    uploaded_file = st.file_uploader("Upload Application Report (Lead Data)", type=['xlsx', 'xls', 'csv'])

with col2:
    uploaded_client_file = st.file_uploader("Upload Client Report Data", type=['xlsx', 'xls', 'csv'])

df_leads = None
df_client = None

if uploaded_file is not None:
    try:
        df_leads = load_data(uploaded_file)
        st.success(f"✅ Lead Data: {len(df_leads)} rows")
    except Exception as e:
        st.error(f"Error loading Lead Data: {e}")

if uploaded_client_file is not None:
    try:
        df_client = load_data(uploaded_client_file)
        st.success(f"✅ Client Data: {len(df_client)} rows")
    except Exception as e:
        st.error(f"Error loading Client Data: {e}")

if df_leads is not None:
    st.divider()
    st.subheader("📊 Application Report Summary")
    
    summary_df = process_application_report(df_leads)
    
    if summary_df is not None:
        st.dataframe(summary_df, use_container_width=True)
        
        # Download Button
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
        st.download_button(
            label="💾 Download Summary Excel",
            data=buffer.getvalue(),
            file_name=f"Application_Summary_{datetime.now().date()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


    # ... (Previous code for Application Report Summary) ...
    
    st.divider()
    st.subheader("✅ Completed Applications Report")
    
    # --- Filters ---
    st.write("### Filters")
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    
    with filter_col1:
        # Status Filter
        all_statuses = df_leads['Status'].unique().tolist()
        # Default to 'Completed' if available, else first item
        default_idx = all_statuses.index('Completed') if 'Completed' in all_statuses else 0
        selected_status = st.selectbox("Status", all_statuses, index=default_idx)
        
    with filter_col2:
        # Time Period Filter (Last Updated)
        # Ensure 'Last Updated' is datetime
        if 'Last Updated' in df_leads.columns:
            try:
                df_leads['Last Updated'] = pd.to_datetime(df_leads['Last Updated'], dayfirst=True, errors='coerce')
                min_date = df_leads['Last Updated'].min().date() if not df_leads['Last Updated'].isnull().all() else datetime.today().date()
                max_date = df_leads['Last Updated'].max().date() if not df_leads['Last Updated'].isnull().all() else datetime.today().date()
                
                date_range = st.date_input("Last Updated Period", value=(min_date, max_date))
            except Exception as e:
                st.warning(f"Could not parse 'Last Updated' dates: {e}")
                date_range = None
        else:
            st.warning("'Last Updated' column not found.")
            date_range = None

    with filter_col3:
        # Workflow Name Filter
        all_workflows = df_leads['Workflow Name'].unique().tolist()
        selected_workflows = st.multiselect("Workflow Name", all_workflows)

    # --- Processing for Completed Report ---
    try:
        # 1. Apply Status Filter
        df_completed = df_leads[df_leads['Status'] == selected_status].copy()
        
        # 2. Apply Date Filter
        if date_range and len(date_range) == 2 and 'Last Updated' in df_completed.columns:
            start_date, end_date = date_range
            # Convert dates to timestamp for comparison
            # Ensure proper type, though pd.to_datetime already done above on df_leads
            mask_date = (df_completed['Last Updated'].dt.date >= start_date) & (df_completed['Last Updated'].dt.date <= end_date)
            df_completed = df_completed[mask_date]
            
        # 3. Apply Workflow Filter
        if selected_workflows:
            df_completed = df_completed[df_completed['Workflow Name'].isin(selected_workflows)]
            
        # 4. Aggregation
        # Group by Application Owner -> Count of Applications
        summary_completed = df_completed.groupby('Application Owner').agg(
            Application_Count=('Internal Client ID', 'count') # Using count of IDs as proxy for application count
        ).reset_index()
        
        # Add Grand Total
        total_completed_row = pd.DataFrame({
            'Application Owner': ['Grand Total'],
            'Application_Count': [len(df_completed)]
        })
        summary_completed = pd.concat([summary_completed, total_completed_row], ignore_index=True)
        
        # Display
        st.dataframe(summary_completed, use_container_width=True)
        
        # Download
        buffer_comp = io.BytesIO()
        with pd.ExcelWriter(buffer_comp, engine='xlsxwriter') as writer:
            summary_completed.to_excel(writer, sheet_name='Completed Apps', index=False)
            
        st.download_button(
            label=f"💾 Download {selected_status} Report",
            data=buffer_comp.getvalue(),
            file_name=f"{selected_status}_Summary_{datetime.now().date()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_completed"
        )
        
    except Exception as e:
        st.error(f"Error generating Completed report: {e}")
