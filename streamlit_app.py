import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Farmacia Melmar Med Sync", layout="wide")

st.title("💊 Farmacia Melmar Med Sync Manager")
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
    "🧑‍⚕️ Manage Patients & Rx", 
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
# TAB 2: Manage Patients & Rx (New ➕ and ✏️ Features)
# ---------------------------------------------------------
with tab2:
    st.subheader("Patient Management")
    
    # Get a list of unique patient IDs currently in the system
    unique_patients = list(set([p["Patient ID"] for p in st.session_state.patients]))
    unique_patients.insert(0, "--- Create New Patient ---")
    
    selected_patient = st.selectbox("Select Patient", unique_patients)
    
    if selected_patient == "--- Create New Patient ---":
        st.markdown("### ➕ Register New Patient")
        with st.form("new_patient_form"):
            p_id = st.text_input("New Patient ID (e.g., PAT-5542)")
            rx_num = st.text_input("Rx Number (e.g., RX-99881)")
            med_name = st.text_input("Medication Name & Strength", placeholder="e.g., Metformin 500mg")
            col1, col2 = st.columns(2)
            with col1:
                days_supply = st.number_input("Days Supply", min_value=1, value=30, key="new_ds")
            with col2:
                quantity = st.number_input("Quantity / Amount", min_value=1, value=30, key="new_qty")
                
            cycle_opt = st.selectbox("Cycle Type", [30, 90, 28], key="new_cycle")
            sync_date = st.date_input("Initial Next Sync Date", datetime.today() + timedelta(days=30), key="new_date")
            
            if st.form_submit_button("Save New Patient & Rx"):
                if p_id and rx_num and med_name:
                    st.session_state.patients.append({
                        "Patient ID": p_id, "Next Sync Date": sync_date, "Cycle": cycle_opt,
                        "Rx Number": rx_num, "Medication": med_name, "Days Supply": int(days_supply),
                        "Quantity": int(quantity), "Status": "Active"
                    })
                    st.success(f"Created profile for {p_id} successfully!")
                    st.rerun()
                else:
                    st.error("Please fill out Patient ID, Rx Number, and Medication fields.")
                    
    else:
        # Show existing patient details
        st.markdown(f"### Profile: `{selected_patient}`")
        patient_records = [p for p in st.session_state.patients if p["Patient ID"] == selected_patient]
        
        st.dataframe(pd.DataFrame(patient_records)[["Rx Number", "Medication", "Days Supply", "Quantity", "Next Sync Date"]], use_container_width=True)
        
        action = st.radio("What would you like to do?", ["➕ Add New Medication to this Patient", "✏️ Edit an Existing Medication"])
        
        if action == "➕ Add New Medication to this Patient":
            with st.form("add_med_form"):
                st.markdown(f"**Add Rx for {selected_patient}**")
                rx_num = st.text_input("Rx Number")
                med_name = st.text_input("Medication Name & Strength")
                col1, col2 = st.columns(2)
                with col1:
                    days_supply = st.number_input("Days Supply", min_value=1, value=30, key="add_ds")
                with col2:
                    quantity = st.number_input("Quantity / Amount", min_value=1, value=30, key="add_qty")
                    
                cycle_opt = st.selectbox("Cycle Type", [30, 90, 28], key="add_cycle")
                sync_date = st.date_input("Initial Next Sync Date", datetime.today() + timedelta(days=30), key="add_date")
                
                if st.form_submit_button("➕ Add Medication"):
                    if rx_num and med_name:
                        st.session_state.patients.append({
                            "Patient ID": selected_patient, "Next Sync Date": sync_date, "Cycle": cycle_opt,
                            "Rx Number": rx_num, "Medication": med_name, "Days Supply": int(days_supply),
                            "Quantity": int(quantity), "Status": "Active"
                        })
                        st.success(f"Added {med_name} to {selected_patient}'s profile!")
                        st.rerun()
                    else:
                        st.error("Rx Number and Medication are required.")
                        
        elif action == "✏️ Edit an Existing Medication":
            rx_to_edit = st.selectbox("Select which Rx to edit", [p["Rx Number"] + " - " + p["Medication"] for p in patient_records])
            
            if rx_to_edit:
                selected_rx_num = rx_to_edit.split(" - ")[0]
                # Find exact index in the master list
                med_idx = next(i for i, p in enumerate(st.session_state.patients) if p["Rx Number"] == selected_rx_num)
                med_data = st.session_state.patients[med_idx]
                
                with st.form("edit_med_form"):
                    st.markdown(f"**Editing {rx_to_edit}**")
                    new_med = st.text_input("Medication Name & Strength", value=med_data["Medication"])
                    col1, col2 = st.columns(2)
                    with col1:
                        new_ds = st.number_input("Days Supply", min_value=1, value=int(med_data["Days Supply"]))
                    with col2:
                        new_qty = st.number_input("Quantity / Amount", min_value=1, value=int(med_data["Quantity"]))
                        
                    new_cycle = st.selectbox("Cycle Type", [30, 90, 28], index=[30, 90, 28].index(med_data["Cycle"]))
                    new_date = st.date_input("Next Sync Date", value=med_data["Next Sync Date"])
                    
                    if st.form_submit_button("✏️ Save Changes"):
                        st.session_state.patients[med_idx].update({
                            "Medication": new_med,
                            "Days Supply": new_ds,
                            "Quantity": new_qty,
                            "Cycle": new_cycle,
                            "Next Sync Date": new_date
                        })
                        st.success("Prescription updated successfully!")
                        st.rerun()

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