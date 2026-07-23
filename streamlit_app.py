import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Pharmacy Med Sync Manager", layout="wide")

st.title("💊 Pharmacy Med Sync & Refill Manager")
st.caption("HIPAA-Safe Mode: Patient ID tracking with automated cycle scheduling and dispensing logs.")

# Initialize Session State
if "patients" not in st.session_state:
    st.session_state.patients = [
        {
            "Patient ID": "PAT-1001",
            "Next Sync Date": datetime.today().date(),
            "Cycle": 30,
            "Rx Number": "RX-45892",
            "Medication": "Lisinopril 10mg",
            "Days Supply": 30,
            "Quantity": 30,
            "Status": "Active"
        }
    ]

if "dispense_history" not in st.session_state:
    st.session_state.dispense_history = []

# Tabs Layout
tab1, tab2, tab3, tab4 = st.tabs([
    "📋 Generate Fill List", 
    "➕ Add / Edit Patient", 
    "📦 Dispense Log", 
    "⚙️ Master Registry"
])

# ---------------------------------------------------------
# TAB 1: Generate Fill List
# ---------------------------------------------------------
with tab1:
    st.subheader("Target Fill Date Generator")
    
    target_fill_date = st.date_input("Select Target Fill Date", datetime.today())
    
    st.markdown("### Matching Fill List")
    fill_candidates = []
    
    for idx, p in enumerate(st.session_state.patients):
        if p["Status"] == "Active" and p["Next Sync Date"] == target_fill_date:
            fill_candidates.append({
                "Index": idx,
                "Patient ID": p["Patient ID"],
                "Rx Number": p["Rx Number"],
                "Medication": p["Medication"],
                "Days Supply": p["Days Supply"],
                "Quantity": p["Quantity"],
                "Cycle": p["Cycle"],
                "Scheduled Date": p["Next Sync Date"]
            })
            
    df_fill = pd.DataFrame(fill_candidates)
    
    if not df_fill.empty:
        st.dataframe(df_fill.drop(columns=["Index"]), use_container_width=True)
        
        st.markdown("### Process & Dispense")
        selected_idx = st.selectbox(
            "Select Patient Index to Dispense", 
            df_fill["Index"], 
            format_func=lambda x: f"{st.session_state.patients[x]['Patient ID']} - {st.session_state.patients[x]['Medication']}"
        )
        
        if st.button("Mark as Dispensed & Auto-Sync"):
            pat = st.session_state.patients[selected_idx]
            
            # Log dispense action
            st.session_state.dispense_history.append({
                "Patient ID": pat["Patient ID"],
                "Rx Number": pat["Rx Number"],
                "Medication": pat["Medication"],
                "Quantity Dispensed": pat["Quantity"],
                "Days Supply": pat["Days Supply"],
                "Dispensed Date": datetime.today().date()
            })
            
            # Calculate next sync date (automated rules: 28 days or 30 days supply = 2 days prior)
            days_sup = int(pat["Days Supply"])
            if days_sup >= 30:
                next_sync = pat["Next Sync Date"] + timedelta(days=days_sup - 2)
            else:
                next_sync = pat["Next Sync Date"] + timedelta(days=days_sup)
                
            st.session_state.patients[selected_idx]["Next Sync Date"] = next_sync
            st.success(f"Dispensed successfully! Next sync date automatically updated to {next_sync}.")
            st.rerun()
    else:
        st.info(f"No patients scheduled for fill on {target_fill_date}.")

# ---------------------------------------------------------
# TAB 2: Add / Edit Patient & Medications
# ---------------------------------------------------------
with tab2:
    st.subheader("Manage Patient & Prescription Details")
    
    with st.form("patient_form"):
        p_id = st.text_input("Patient ID (e.g., PAT-5542)")
        rx_num = st.text_input("Rx Number (e.g., RX-99881)")
        med_name = st.text_input("Medication Name & Strength", placeholder="e.g., Metformin 500mg")
        
        col1, col2 = st.columns(2)
        with col1:
            days_supply = st.number_input("Days Supply", min_value=1, value=30)
        with col2:
            quantity = st.number_input("Quantity / Amount", min_value=1, value=30)
            
        cycle_opt = st.selectbox("Cycle Type", [30, 90, 28])
        sync_date = st.date_input("Initial Next Sync Date", datetime.today() + timedelta(days=30))
        
        submitted = st.form_submit_button("Save Patient & Rx")
        
        if submitted:
            if p_id and rx_num and med_name:
                st.session_state.patients.append({
                    "Patient ID": p_id,
                    "Next Sync Date": sync_date,
                    "Cycle": cycle_opt,
                    "Rx Number": rx_num,
                    "Medication": med_name,
                    "Days Supply": int(days_supply),
                    "Quantity": int(quantity),
                    "Status": "Active"
                })
                st.success(f"Added prescription for {p_id} successfully!")
            else:
                st.error("Please fill out Patient ID, Rx Number, and Medication fields.")

# ---------------------------------------------------------
# TAB 3: Dispense Log
# ---------------------------------------------------------
with tab3:
    st.subheader("Dispensed Medications History")
    df_history = pd.DataFrame(st.session_state.dispense_history)
    if not df_history.empty:
        st.dataframe(df_history, use_container_width=True)
    else:
        st.info("No medications dispensed yet.")

# ---------------------------------------------------------
# TAB 4: Master Registry
# ---------------------------------------------------------
with tab4:
    st.subheader("Master Patient Sync Registry")
    st.dataframe(pd.DataFrame(st.session_state.patients), use_container_width=True)