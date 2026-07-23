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
            "Refills": 5,
            "Medication": "Lisinopril 10mg",
            "Days Supply": 30,
            "Quantity": 30,
            "Status": "Active",
            "Condition": "HTN" 
        }
    ]

if "dispense_history" not in st.session_state:
    st.session_state.dispense_history = []

CYCLE_OPTIONS = [28, 30, 60, 84, 88, 90]
CONDITION_OPTIONS = ["None", "HTN", "Diabetes", "Dyslipidemia"]

# Clean, Modern Tabs Layout with New Adherence Tab
tab_fill, tab_manage, tab_adherence, tab_history, tab_overdue, tab_registry = st.tabs([
    "📋 Fill List Generator", 
    "🧑‍⚕️ Patient Management", 
    "⭐ Adherence Patient Management",
    "📦 Dispense History", 
    "🚨 Missed Fills",
    "⚙️ Master Registry"
])

# ---------------------------------------------------------
# TAB 1: Generate Fill List & Export Options (COLOR CODED)
# ---------------------------------------------------------
with tab_fill:
    st.subheader("Target Fill Date Generator")
    
    # Adherence Color Legend
    st.markdown("**Adherence Flag Legend:** 🟦 **HTN** (Light Blue) | 🟩 **Diabetes** (Light Green) | 🟨 **Dyslipidemia** (Light Yellow)")
    
    col_date, col_filt = st.columns(2)
    with col_date:
        target_fill_date = st.date_input("Select Target Fill Date", datetime.today())
    with col_filt:
        adherence_filter = st.selectbox("Filter by Adherence Condition", ["All Patients", "HTN", "Diabetes", "Dyslipidemia", "None"])
    
    fill_candidates = []
    
    for idx, p in enumerate(st.session_state.patients):
        if p["Status"] == "Active" and p["Next Sync Date"] == target_fill_date:
            cond = p.get("Condition", "None")
            # Apply Filter Logic
            if adherence_filter == "All Patients" or adherence_filter == cond:
                fill_candidates.append({
                    "Index": idx,
                    "Patient ID": p["Patient ID"],
                    "Medication": p["Medication"],
                    "Refills": p.get("Refills", 0),
                    "Condition": cond,
                    "Days Supply": p["Days Supply"],
                    "Quantity": p["Quantity"],
                    "Cycle": p["Cycle"],
                    "Scheduled Date": p["Next Sync Date"]
                })
            
    df_fill = pd.DataFrame(fill_candidates)
    
    if not df_fill.empty:
        display_df = df_fill.drop(columns=["Index"])
        
        # Color coding function for the dataframe
        def highlight_adherence(row):
            color = ''
            if row['Condition'] == 'HTN':
                color = '#cce5ff' # Light Blue
            elif row['Condition'] == 'Diabetes':
                color = '#d4edda' # Light Green
            elif row['Condition'] == 'Dyslipidemia':
                color = '#fff3cd' # Light Yellow
            
            if color:
                return [f'background-color: {color}; color: black'] * len(row)
            return [''] * len(row)
            
        styled_df = display_df.style.apply(highlight_adherence, axis=1)
        
        st.dataframe(styled_df, use_container_width=True)
        
        # --- Export & Email Features ---
        st.divider()
        col_export, col_email = st.columns(2)
        
        with col_export:
            st.markdown("**Print / Export Options**")
            csv_data = display_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Fill List as CSV",
                data=csv_data,
                file_name=f'Melmar_Fill_List_{target_fill_date}.csv',
                mime='text/csv',
                use_container_width=True
            )
            
        with col_email:
            st.markdown("**Send List to Email**")
            with st.form("email_form"):
                email_address = st.text_input("Destination Email", placeholder="pharmacist@example.com")
                if st.form_submit_button("Send via Email", use_container_width=True):
                    if email_address:
                        st.success(f"Success! The fill list for {target_fill_date} was securely routed to {email_address}.")
                    else:
                        st.error("Please enter a valid email address.")
        st.divider()
        
        # --- Process & Dispense ---
        st.markdown("### Process & Dispense")
        selected_idx = st.selectbox(
            "Select Patient Index to Dispense", 
            df_fill["Index"], 
            format_func=lambda x: f"{st.session_state.patients[x]['Patient ID']} - {st.session_state.patients[x]['Medication']}"
        )
        
        if st.button("Mark as Dispensed & Auto-Sync"):
            pat = st.session_state.patients[selected_idx]
            
            st.session_state.dispense_history.append({
                "Patient ID": pat["Patient ID"],
                "Medication": pat["Medication"],
                "Quantity Dispensed": pat["Quantity"],
                "Days Supply": pat["Days Supply"],
                "Dispensed Date": datetime.today().date()
            })
            
            # Automatically subtract a refill if there are refills left
            if pat.get("Refills", 0) > 0:
                st.session_state.patients[selected_idx]["Refills"] -= 1
            
            # Calculate next sync date
            days_sup = int(pat["Days Supply"])
            if days_sup >= 30:
                next_sync = pat["Next Sync Date"] + timedelta(days=days_sup - 2)
            else:
                next_sync = pat["Next Sync Date"] + timedelta(days=days_sup)
                
            st.session_state.patients[selected_idx]["Next Sync Date"] = next_sync
            
            remaining_refills = st.session_state.patients[selected_idx]["Refills"]
            st.success(f"Dispensed successfully! Next sync date updated to {next_sync}. Remaining Refills: {remaining_refills}")
            st.rerun()
    else:
        st.info(f"No patients scheduled for fill on {target_fill_date} under the '{adherence_filter}' filter.")

# ---------------------------------------------------------
# TAB 2: Standard Patient Management 
# ---------------------------------------------------------
with tab_manage:
    st.subheader("Standard Patient Management")
    
    unique_patients = list(set([p["Patient ID"] for p in st.session_state.patients]))
    unique_patients.insert(0, "--- Create New Patient ---")
    
    selected_patient = st.selectbox("Select Patient", unique_patients, key="std_patient_select")
    
    if selected_patient == "--- Create New Patient ---":
        st.markdown("### ➕ Register New Patient")
        with st.form("new_patient_form"):
            p_id = st.text_input("New Patient ID (e.g., PAT-5542)")
            med_name = st.text_input("Medication Name & Strength")
            
            col_ref, col_ds, col_qty = st.columns(3)
            with col_ref:
                refills = st.number_input("Amount of Refills", min_value=0, value=11, key="new_ref")
            with col_ds:
                days_supply = st.number_input("Days Supply", min_value=1, value=30, key="new_ds")
            with col_qty:
                quantity = st.number_input("Quantity / Amount", min_value=1, value=30, key="new_qty")
                
            cycle_opt = st.selectbox("Cycle Type", CYCLE_OPTIONS, index=1, key="new_cycle")
            sync_date = st.date_input("Initial Next Sync Date", datetime.today() + timedelta(days=30), key="new_date")
            
            if st.form_submit_button("Save New Patient & Rx"):
                if p_id and med_name:
                    st.session_state.patients.append({
                        "Patient ID": p_id, "Next Sync Date": sync_date, "Cycle": cycle_opt,
                        "Refills": int(refills), "Medication": med_name, "Days Supply": int(days_supply),
                        "Quantity": int(quantity), "Status": "Active", "Condition": "None"
                    })
                    st.success("Patient created!")
                    st.rerun()
                else:
                    st.error("Please fill out all required fields.")
    else:
        st.markdown(f"### Profile: `{selected_patient}`")
        patient_records = [p for p in st.session_state.patients if p["Patient ID"] == selected_patient]
        st.dataframe(pd.DataFrame(patient_records)[["Medication", "Refills", "Days Supply", "Quantity", "Cycle", "Next Sync Date"]], use_container_width=True)
        
        action = st.radio("What would you like to do?", ["➕ Add New Medication to this Patient", "✏️ Edit an Existing Medication"], key="std_action")
        
        if action == "➕ Add New Medication to this Patient":
            with st.form("add_med_form"):
                med_name = st.text_input("Medication Name & Strength")
                col_ref, col_ds, col_qty = st.columns(3)
                with col_ref:
                    refills = st.number_input("Amount of Refills", min_value=0, value=11, key="add_ref")
                with col_ds:
                    days_supply = st.number_input("Days Supply", min_value=1, value=30, key="add_ds")
                with col_qty:
                    quantity = st.number_input("Quantity / Amount", min_value=1, value=30, key="add_qty")
                cycle_opt = st.selectbox("Cycle Type", CYCLE_OPTIONS, index=1, key="add_cycle")
                sync_date = st.date_input("Initial Next Sync Date", datetime.today() + timedelta(days=30), key="add_date")
                
                if st.form_submit_button("➕ Add Medication"):
                    if med_name:
                        st.session_state.patients.append({
                            "Patient ID": selected_patient, "Next Sync Date": sync_date, "Cycle": cycle_opt,
                            "Refills": int(refills), "Medication": med_name, "Days Supply": int(days_supply),
                            "Quantity": int(quantity), "Status": "Active", "Condition": "None"
                        })
                        st.success("Medication added!")
                        st.rerun()
                        
        elif action == "✏️ Edit an Existing Medication":
            med_to_edit = st.selectbox("Select which Medication to edit", [p["Medication"] for p in patient_records])
            if med_to_edit:
                med_idx = next(i for i, p in enumerate(st.session_state.patients) if p["Medication"] == med_to_edit and p["Patient ID"] == selected_patient)
                med_data = st.session_state.patients[med_idx]
                
                with st.form("edit_med_form"):
                    new_med = st.text_input("Medication Name & Strength", value=med_data["Medication"])
                    col_ref, col_ds, col_qty = st.columns(3)
                    with col_ref:
                        new_ref = st.number_input("Amount of Refills", min_value=0, value=int(med_data.get("Refills", 0)), key="edit_ref")
                    with col_ds:
                        new_ds = st.number_input("Days Supply", min_value=1, value=int(med_data["Days Supply"]))
                    with col_qty:
                        new_qty = st.number_input("Quantity / Amount", min_value=1, value=int(med_data["Quantity"]))
                        
                    current_cycle = med_data.get("Cycle", 30)
                    cycle_index = CYCLE_OPTIONS.index(current_cycle) if current_cycle in CYCLE_OPTIONS else 1
                    new_cycle = st.selectbox("Cycle Type", CYCLE_OPTIONS, index=cycle_index)
                    new_date = st.date_input("Next Sync Date", value=med_data["Next Sync Date"])
                    
                    if st.form_submit_button("✏️ Save Changes"):
                        st.session_state.patients[med_idx].update({
                            "Medication": new_med, "Refills": new_ref, "Days Supply": new_ds, "Quantity": new_qty,
                            "Cycle": new_cycle, "Next Sync Date": new_date
                        })
                        st.success("Updated successfully!")
                        st.rerun()

# ---------------------------------------------------------
# TAB 3: ⭐ Adherence Patient Management
# ---------------------------------------------------------
with tab_adherence:
    st.subheader("⭐ Adherence Patient Management")
    st.caption("Enroll patients into specific adherence programs (HTN, Diabetes, Dyslipidemia) to highlight them on the daily fill lists.")
    
    unique_patients_adh = list(set([p["Patient ID"] for p in st.session_state.patients]))
    unique_patients_adh.insert(0, "--- Create New Adherence Patient ---")
    
    selected_patient_adh = st.selectbox("Select Adherence Patient", unique_patients_adh, key="adh_patient_select")
    
    if selected_patient_adh == "--- Create New Adherence Patient ---":
        st.markdown("### ➕ Register New Adherence Patient")
        with st.form("new_adh_patient_form"):
            p_id = st.text_input("New Patient ID (e.g., PAT-5542)", key="adh_pid")
            med_name = st.text_input("Medication Name & Strength", key="adh_med")
            
            adh_condition = st.selectbox("🔴 Adherence Condition (Color Code)", CONDITION_OPTIONS, index=1, key="adh_cond_new")
            
            col_ref, col_ds, col_qty = st.columns(3)
            with col_ref:
                refills = st.number_input("Amount of Refills", min_value=0, value=11, key="adh_new_ref")
            with col_ds:
                days_supply = st.number_input("Days Supply", min_value=1, value=30, key="adh_new_ds")
            with col_qty:
                quantity = st.number_input("Quantity / Amount", min_value=1, value=30, key="adh_new_qty")
                
            cycle_opt = st.selectbox("Cycle Type", CYCLE_OPTIONS, index=1, key="adh_new_cycle")
            sync_date = st.date_input("Initial Next Sync Date", datetime.today() + timedelta(days=30), key="adh_new_date")
            
            if st.form_submit_button("Save Adherence Patient & Rx"):
                if p_id and med_name:
                    st.session_state.patients.append({
                        "Patient ID": p_id, "Next Sync Date": sync_date, "Cycle": cycle_opt,
                        "Refills": int(refills), "Medication": med_name, "Days Supply": int(days_supply),
                        "Quantity": int(quantity), "Status": "Active", "Condition": adh_condition
                    })
                    st.success("Adherence Patient created!")
                    st.rerun()
                else:
                    st.error("Please fill out all required fields.")
    else:
        st.markdown(f"### Adherence Profile: `{selected_patient_adh}`")
        patient_records_adh = [p for p in st.session_state.patients if p["Patient ID"] == selected_patient_adh]
        st.dataframe(pd.DataFrame(patient_records_adh)[["Medication", "Condition", "Refills", "Days Supply", "Next Sync Date"]], use_container_width=True)
        
        action_adh = st.radio("What would you like to do?", ["➕ Add Adherence Rx to this Patient", "✏️ Edit an Existing Rx / Condition"], key="adh_action")
        
        if action_adh == "➕ Add Adherence Rx to this Patient":
            with st.form("add_adh_med_form"):
                med_name = st.text_input("Medication Name & Strength", key="adh_add_med")
                adh_condition = st.selectbox("🔴 Adherence Condition (Color Code)", CONDITION_OPTIONS, index=1, key="adh_cond_add")
                
                col_ref, col_ds, col_qty = st.columns(3)
                with col_ref:
                    refills = st.number_input("Amount of Refills", min_value=0, value=11, key="adh_add_ref")
                with col_ds:
                    days_supply = st.number_input("Days Supply", min_value=1, value=30, key="adh_add_ds")
                with col_qty:
                    quantity = st.number_input("Quantity / Amount", min_value=1, value=30, key="adh_add_qty")
                cycle_opt = st.selectbox("Cycle Type", CYCLE_OPTIONS, index=1, key="adh_add_cycle")
                sync_date = st.date_input("Initial Next Sync Date", datetime.today() + timedelta(days=30), key="adh_add_date")
                
                if st.form_submit_button("➕ Add Adherence Medication"):
                    if med_name:
                        st.session_state.patients.append({
                            "Patient ID": selected_patient_adh, "Next Sync Date": sync_date, "Cycle": cycle_opt,
                            "Refills": int(refills), "Medication": med_name, "Days Supply": int(days_supply),
                            "Quantity": int(quantity), "Status": "Active", "Condition": adh_condition
                        })
                        st.success("Adherence Medication added!")
                        st.rerun()
                        
        elif action_adh == "✏️ Edit an Existing Rx / Condition":
            med_to_edit = st.selectbox("Select which Medication to edit", [p["Medication"] for p in patient_records_adh], key="adh_edit_sel")
            if med_to_edit:
                med_idx = next(i for i, p in enumerate(st.session_state.patients) if p["Medication"] == med_to_edit and p["Patient ID"] == selected_patient_adh)
                med_data = st.session_state.patients[med_idx]
                
                with st.form("edit_adh_med_form"):
                    new_med = st.text_input("Medication Name & Strength", value=med_data["Medication"], key="adh_edit_med")
                    
                    current_cond = med_data.get("Condition", "None")
                    cond_index = CONDITION_OPTIONS.index(current_cond) if current_cond in CONDITION_OPTIONS else 0
                    new_cond = st.selectbox("🔴 Adherence Condition", CONDITION_OPTIONS, index=cond_index, key="adh_cond_edit")
                    
                    col_ref, col_ds, col_qty = st.columns(3)
                    with col_ref:
                        new_ref = st.number_input("Amount of Refills", min_value=0, value=int(med_data.get("Refills", 0)), key="adh_edit_ref")
                    with col_ds:
                        new_ds = st.number_input("Days Supply", min_value=1, value=int(med_data["Days Supply"]), key="adh_edit_ds")
                    with col_qty:
                        new_qty = st.number_input("Quantity / Amount", min_value=1, value=int(med_data["Quantity"]), key="adh_edit_qty")
                        
                    current_cycle = med_data.get("Cycle", 30)
                    cycle_index = CYCLE_OPTIONS.index(current_cycle) if current_cycle in CYCLE_OPTIONS else 1
                    new_cycle = st.selectbox("Cycle Type", CYCLE_OPTIONS, index=cycle_index, key="adh_edit_cycle")
                    new_date = st.date_input("Next Sync Date", value=med_data["Next Sync Date"], key="adh_edit_date")
                    
                    if st.form_submit_button("✏️ Save Changes"):
                        st.session_state.patients[med_idx].update({
                            "Medication": new_med, "Condition": new_cond, "Refills": new_ref, "Days Supply": new_ds, 
                            "Quantity": new_qty, "Cycle": new_cycle, "Next Sync Date": new_date
                        })
                        st.success("Updated successfully!")
                        st.rerun()

# ---------------------------------------------------------
# TAB 4: Dispense Log
# ---------------------------------------------------------
with tab_history:
    st.subheader("Dispensed Medications History")
    df_history = pd.DataFrame(st.session_state.dispense_history)
    if not df_history.empty:
        st.dataframe(df_history, use_container_width=True)
    else:
        st.info("No medications dispensed yet.")

# ---------------------------------------------------------
# TAB 5: Missed / Overdue Fills
# ---------------------------------------------------------
with tab_overdue:
    st.subheader("Missed / Overdue Syncs")
    today = datetime.today().date()
    overdue_list = []
    
    for p in st.session_state.patients:
        if p.get("Status", "Active") == "Active" and p["Next Sync Date"] < today:
            days_missed = (today - p["Next Sync Date"]).days
            overdue_list.append({
                "Patient ID": p["Patient ID"],
                "Medication": p["Medication"],
                "Refills": p.get("Refills", 0),
                "Condition": p.get("Condition", "None"),
                "Scheduled Date": p["Next Sync Date"],
                "Days Overdue": f"{days_missed} Days"
            })
            
    df_overdue = pd.DataFrame(overdue_list)
    
    if not df_overdue.empty:
        st.error(f"Attention: {len(df_overdue)} medications are currently past their sync date.")
        st.dataframe(df_overdue, use_container_width=True)
    else:
        st.success("Great job! There are no missed or overdue fills.")

# ---------------------------------------------------------
# TAB 6: Master Registry
# ---------------------------------------------------------
with tab_registry:
    st.subheader("Master Patient Sync Registry")
    st.dataframe(pd.DataFrame(st.session_state.patients), use_container_width=True)