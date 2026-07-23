import streamlit as st

st.title("🎈 My new app")
st.write(
    "Let's start building! For help and inspiration, head over to [docs.streamlit.io](https://docs.streamlit.io/)."
)
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Pharmacy Med Sync Scheduler", layout="wide")

st.title("💊 Med Sync Schedule Manager")
st.caption("HIPAA-Safe Mode: Uses Patient IDs only. No PHI stored.")

# Initialize local in-memory session data for testing
if "patients" not in st.session_state:
    st.session_state.patients = [
        {"Patient ID": "PAT-1001", "Sync Day": 5, "Cycle": 30, "Status": "Active"},
        {"Patient ID": "PAT-1002", "Sync Day": 12, "Cycle": 30, "Status": "Active"},
        {"Patient ID": "PAT-1003", "Sync Day": 20, "Cycle": 90, "Status": "Active"},
    ]

# Layout Tabs
tab1, tab2, tab3 = st.tabs(["📋 Worklist & Calls", "➕ Add Patient ID", "⚙️ Sync Registry"])

# TAB 1: Monthly Worklist & Action Items
with tab1:
    st.subheader("Upcoming Sync Worklist")
    
    selected_month = st.date_input("Select Target Month", datetime.today())
    target_year = selected_month.year
    target_month = selected_month.month

    # Generate schedules for the selected month
    worklist = []
    for p in st.session_state.patients:
        if p["Status"] == "Active":
            try:
                target_date = datetime(target_year, target_month, p["Sync Day"]).date()
                call_date = target_date - timedelta(days=7) # Call patient 7 days prior
                worklist.append({
                    "Patient ID": p["Patient ID"],
                    "Call Date": call_date,
                    "Target Fill Date": target_date,
                    "Cycle": f"{p['Cycle']} Days",
                    "Status": "Pending Call"
                })
            except ValueError:
                pass # Handles invalid dates like Feb 30

    df_worklist = pd.DataFrame(worklist)
    
    if not df_worklist.empty:
        # Display filtering options
        st.dataframe(df_worklist, use_container_width=True)
        
        # Action Simulator
        st.markdown("### Quick Action")
        col1, col2 = st.columns(2)
        with col1:
            pid = st.selectbox("Select Patient to Process", df_worklist["Patient ID"])
        with col2:
            action = st.selectbox("Mark Status", ["Called - Confirmed", "Called - Left Message", "Fills Queued", "Completed"])
        
        if st.button("Update Status"):
            st.success(f"Updated {pid} to '{action}'")
    else:
        st.info("No syncs scheduled for this month.")

# TAB 2: Add New Patient to Sync
with tab2:
    st.subheader("Register Patient ID for Med Sync")
    with st.form("add_patient_form"):
        new_id = st.text_input("Pharmacy System Patient ID (e.g., PAT-5542)")
        sync_day = st.number_input("Target Sync Day of Month (1-28)", min_value=1, max_value=28, value=10)
        cycle = st.selectbox("Fill Cycle", [30, 90, 28])
        
        submitted = st.form_submit_button("Add to Med Sync")
        if submitted:
            if new_id:
                st.session_state.patients.append({
                    "Patient ID": new_id,
                    "Sync Day": int(sync_day),
                    "Cycle": cycle,
                    "Status": "Active"
                })
                st.success(f"Added {new_id} to Sync Schedule!")
            else:
                st.error("Please enter a valid Patient ID.")

# TAB 3: Master Registry
with tab3:
    st.subheader("Master Patient Sync Registry")
    st.dataframe(pd.DataFrame(st.session_state.patients), use_container_width=True)
    