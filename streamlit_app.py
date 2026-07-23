import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import json
import zipfile
import io
import smtplib
from email.message import EmailMessage

st.set_page_config(page_title="Farmacia Melmar Med Sync", layout="wide")

# --- DATABASE SETUP FOR LOCAL/OFFLINE USE ---
DATA_FILE = "melmar_db.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"patients": [], "dispense_history": []}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump({
            "patients": st.session_state.patients, 
            "dispense_history": st.session_state.dispense_history
        }, f)

# Initialize Session State from Local Database
if "patients" not in st.session_state:
    db = load_data()
    st.session_state.patients = db.get("patients", [])
    st.session_state.dispense_history = db.get("dispense_history", [])

CYCLE_OPTIONS = [28, 30, 60, 84, 88, 90]
CONDITION_OPTIONS = ["None", "HTN", "Diabetes", "Dyslipidemia"]

st.title("💊 Farmacia Melmar Med Sync Manager")
st.caption("HIPAA-Safe Mode: Offline Local Storage with Automated Backup & Reporting.")

# Tabs Layout
tab_fill, tab_manage, tab_adherence, tab_history, tab_overdue, tab_registry, tab_reports, tab_backup = st.tabs([
    " Fill List Generator", 
    " Patient Management", 
    " Adherence",
    " Dispense History", 
    " Missed Fills",
    " Registry",
    " Reports",
    " Backup & Security"
])

# ---------------------------------------------------------
# TAB 1: Generate Fill List & Export Options 
# ---------------------------------------------------------
with tab_fill:
    st.subheader("Target Fill Date Generator")
    st.markdown("**Adherence Flag Legend:** 🟦 **HTN** | 🟩 **Diabetes** | 🟨 **Dyslipidemia**")
    
    col_date, col_filt = st.columns(2)
    with col_date:
        target_fill_date = st.date_input("Select Target Fill Date", datetime.today())
    with col_filt:
        adherence_filter = st.selectbox("Filter by Adherence Condition", ["All Patients", "HTN", "Diabetes", "Dyslipidemia", "None"])
    
    fill_candidates = []
    
    for idx, p in enumerate(st.session_state.patients):
        if p["Status"] == "Active" and p["Next Sync Date"] == str(target_fill_date):
            cond = p.get("Condition", "None")
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
        
        def highlight_adherence(row):
            color = ''
            if row['Condition'] == 'HTN': color = '#cce5ff'
            elif row['Condition'] == 'Diabetes': color = '#d4edda'
            elif row['Condition'] == 'Dyslipidemia': color = '#fff3cd'
            if color: return [f'background-color: {color}; color: black'] * len(row)
            return [''] * len(row)
            
        st.dataframe(display_df.style.apply(highlight_adherence, axis=1), use_container_width=True)
        
        st.divider()
        col_export, col_email = st.columns(2)
        
        csv_data = display_df.to_csv(index=False).encode('utf-8')
        
        with col_export:
            st.markdown("###  Print / Download")
            st.download_button(
                label="Download Fill List as CSV",
                data=csv_data,
                file_name=f'Melmar_Fill_List_{target_fill_date}.csv',
                mime='text/csv',
                use_container_width=True
            )
            
        with col_email:
            st.markdown("### 📧 Email this Fill List")
            with st.form("email_fill_list_form"):
                sender_email = st.text_input("Sender Email (Your Gmail)")
                email_password = st.text_input("App Password", type="password")
                receiver_email = st.text_input("Send List To (Receiver Email)")
                
                if st.form_submit_button("Send Fill List via Email", use_container_width=True):
                    if not sender_email or not email_password or not receiver_email:
                        st.error("Please fill in all email credentials.")
                    else:
                        try:
                            msg = EmailMessage()
                            msg['Subject'] = f'Farmacia Melmar Fill List - {target_fill_date}'
                            msg['From'] = sender_email
                            msg['To'] = receiver_email
                            msg.set_content(f"Attached is the generated Med Sync fill list for {target_fill_date}.")
                            
                            # Attach the CSV file directly to the email
                            msg.add_attachment(csv_data, maintype='text', subtype='csv', filename=f'Fill_List_{target_fill_date}.csv')
                            
                            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                                smtp.login(sender_email, email_password)
                                smtp.send_message(msg)
                                
                            st.success("✅ Fill List successfully emailed!")
                        except Exception as e:
                            st.error(f"Failed to send email. Check your App Password. Error: {e}")
        st.divider()
        
        st.markdown("### Process & Dispense")
        selected_idx = st.selectbox("Select Patient to Dispense", df_fill["Index"], format_func=lambda x: f"{st.session_state.patients[x]['Patient ID']} - {st.session_state.patients[x]['Medication']}")
        
        if st.button("Mark as Dispensed & Auto-Sync"):
            pat = st.session_state.patients[selected_idx]
            
            st.session_state.dispense_history.append({
                "Patient ID": pat["Patient ID"],
                "Medication": pat["Medication"],
                "Quantity Dispensed": pat["Quantity"],
                "Days Supply": pat["Days Supply"],
                "Dispensed Date": str(datetime.today().date())
            })
            
            if pat.get("Refills", 0) > 0:
                st.session_state.patients[selected_idx]["Refills"] -= 1
            
            days_sup = int(pat["Days Supply"])
            target = datetime.strptime(pat["Next Sync Date"], "%Y-%m-%d").date()
            if days_sup >= 30:
                next_sync = target + timedelta(days=days_sup - 2)
            else:
                next_sync = target + timedelta(days=days_sup)
                
            st.session_state.patients[selected_idx]["Next Sync Date"] = str(next_sync)
            save_data() # Save to local drive
            st.success(f"Dispensed successfully! Next sync date updated to {next_sync}.")
            st.rerun()
    else:
        st.info(f"No patients scheduled for fill on {target_fill_date}.")

# ---------------------------------------------------------
# TAB 2 & 3: Standard & Adherence Management
# ---------------------------------------------------------
with tab_manage:
    st.subheader("Standard Patient Management")
    unique_patients = list(set([p["Patient ID"] for p in st.session_state.patients]))
    unique_patients.insert(0, "--- Create New Patient ---")
    selected_patient = st.selectbox("Select Patient", unique_patients, key="std_patient_select")
    
    if selected_patient == "--- Create New Patient ---":
        with st.form("new_patient_form"):
            p_id, med_name = st.text_input("Patient ID"), st.text_input("Medication Name & Strength")
            col_ref, col_ds, col_qty = st.columns(3)
            with col_ref: refills = st.number_input("Refills", min_value=0, value=11)
            with col_ds: days_supply = st.number_input("Days Supply", min_value=1, value=30)
            with col_qty: quantity = st.number_input("Quantity", min_value=1, value=30)
            cycle_opt = st.selectbox("Cycle Type", CYCLE_OPTIONS, index=1)
            sync_date = st.date_input("Initial Sync Date", datetime.today() + timedelta(days=30))
            
            if st.form_submit_button("Save New Patient & Rx"):
                if p_id and med_name:
                    st.session_state.patients.append({
                        "Patient ID": p_id, "Next Sync Date": str(sync_date), "Cycle": cycle_opt,
                        "Refills": int(refills), "Medication": med_name, "Days Supply": int(days_supply),
                        "Quantity": int(quantity), "Status": "Active", "Condition": "None"
                    })
                    save_data()
                    st.success("Patient created!"); st.rerun()
    else:
        patient_records = [p for p in st.session_state.patients if p["Patient ID"] == selected_patient]
        st.dataframe(pd.DataFrame(patient_records)[["Medication", "Refills", "Days Supply", "Next Sync Date"]], use_container_width=True)

with tab_adherence:
    st.subheader(" Adherence Patient Management")
    unique_patients_adh = list(set([p["Patient ID"] for p in st.session_state.patients]))
    unique_patients_adh.insert(0, "--- Create New Adherence Patient ---")
    selected_patient_adh = st.selectbox("Select Adherence Patient", unique_patients_adh, key="adh_patient_select")
    
    if selected_patient_adh == "--- Create New Adherence Patient ---":
        with st.form("new_adh_patient_form"):
            p_id, med_name = st.text_input("Patient ID", key="adh_pid"), st.text_input("Medication", key="adh_med")
            adh_condition = st.selectbox("🔴 Condition (Color Code)", CONDITION_OPTIONS, index=1)
            col_ref, col_ds, col_qty = st.columns(3)
            with col_ref: refills = st.number_input("Refills", min_value=0, value=11, key="adh_new_ref")
            with col_ds: days_supply = st.number_input("Days Supply", min_value=1, value=30, key="adh_new_ds")
            with col_qty: quantity = st.number_input("Quantity", min_value=1, value=30, key="adh_new_qty")
            cycle_opt = st.selectbox("Cycle Type", CYCLE_OPTIONS, index=1, key="adh_new_cycle")
            sync_date = st.date_input("Initial Sync Date", datetime.today() + timedelta(days=30), key="adh_new_date")
            
            if st.form_submit_button("Save Adherence Patient & Rx"):
                if p_id and med_name:
                    st.session_state.patients.append({
                        "Patient ID": p_id, "Next Sync Date": str(sync_date), "Cycle": cycle_opt,
                        "Refills": int(refills), "Medication": med_name, "Days Supply": int(days_supply),
                        "Quantity": int(quantity), "Status": "Active", "Condition": adh_condition
                    })
                    save_data()
                    st.success("Adherence Patient created!"); st.rerun()
    else:
        patient_records_adh = [p for p in st.session_state.patients if p["Patient ID"] == selected_patient_adh]
        st.dataframe(pd.DataFrame(patient_records_adh)[["Medication", "Condition", "Refills", "Next Sync Date"]], use_container_width=True)

# ---------------------------------------------------------
# TAB 4, 5, 6: History, Overdue, Registry
# ---------------------------------------------------------
with tab_history:
    st.subheader("Dispense History Log")
    st.dataframe(pd.DataFrame(st.session_state.dispense_history), use_container_width=True)

with tab_overdue:
    st.subheader(" Missed / Overdue Syncs")
    today_str = str(datetime.today().date())
    overdue_list = [p for p in st.session_state.patients if p.get("Status") == "Active" and p["Next Sync Date"] < today_str]
    st.dataframe(pd.DataFrame(overdue_list), use_container_width=True)

with tab_registry:
    st.subheader("Master Patient Registry")
    st.dataframe(pd.DataFrame(st.session_state.patients), use_container_width=True)

# ---------------------------------------------------------
# TAB 7:  REPORTS (NEW)
# ---------------------------------------------------------
with tab_reports:
    st.subheader(" Pharmacy Reports & Analytics")
    
    st.markdown("### Upcoming Workload")
    total_active = len([p for p in st.session_state.patients if p.get("Status") == "Active"])
    st.metric(label="Total Active Med Sync Prescriptions Scheduled", value=total_active)
    
    st.divider()
    
    st.markdown("### Dispensing Date Range Report")
    st.caption("Select a date range to see how many prescriptions were dispensed in that period.")
    
    col_start, col_end = st.columns(2)
    with col_start:
        start_date = st.date_input("Start Date", datetime.today().date() - timedelta(days=30))
    with col_end:
        end_date = st.date_input("End Date", datetime.today().date())
        
    if start_date <= end_date:
        dispensed_in_range = []
        for record in st.session_state.dispense_history:
            try:
                # Convert the saved string date back into a date object to compare
                disp_date = datetime.strptime(record["Dispensed Date"], "%Y-%m-%d").date()
                if start_date <= disp_date <= end_date:
                    dispensed_in_range.append(record)
            except:
                pass
                
        df_report = pd.DataFrame(dispensed_in_range)
        
        st.metric(label=f"Total Prescriptions Dispensed ({start_date} to {end_date})", value=len(dispensed_in_range))
        
        if not df_report.empty:
            st.dataframe(df_report, use_container_width=True)
            csv_report = df_report.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Report Data (CSV)", 
                data=csv_report, 
                file_name=f"Melmar_Report_{start_date}_to_{end_date}.csv", 
                mime='text/csv'
            )
        else:
            st.info("No prescriptions were dispensed in this date range.")
    else:
        st.error("Error: Start Date must be before End Date.")

# ---------------------------------------------------------
# TAB 8:  Backup & Security (ZIP & EMAIL)
# ---------------------------------------------------------
with tab_backup:
    st.subheader(" Offline Data Backup & Export")
    st.caption("Your data is safely stored offline on this computer. Use these tools to back it up.")
    
    # 1. Manual ZIP Download
    st.markdown("### 1. Download Compressed ZIP Backup")
    if os.path.exists(DATA_FILE):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(DATA_FILE, arcname="melmar_database_backup.json")
        buf.seek(0)
        
        st.download_button(
            label="📦 Download ZIP Backup",
            data=buf,
            file_name=f"Melmar_Backup_{datetime.today().date()}.zip",
            mime="application/zip",
            use_container_width=True
        )
    else:
        st.warning("No data file found yet. Add a patient first to create the database.")
        
    st.divider()
    
    # 2. Automated Email Backup
    st.markdown("### 2. Email ZIP Backup Off-Site")
    st.info("To send automated emails, use a Gmail account. You must generate an 'App Password' in your Google Account Security settings.")
    
    with st.form("email_backup_form"):
        col1, col2 = st.columns(2)
        with col1:
            sender_email = st.text_input("Sender Email (Your Gmail)")
            email_password = st.text_input("App Password", type="password")
        with col2:
            receiver_email = st.text_input("Send Backup To (Receiver Email)")
            
        if st.form_submit_button("Securely Email ZIP Backup"):
            if not sender_email or not email_password or not receiver_email:
                st.error("Please fill in all email credentials.")
            elif not os.path.exists(DATA_FILE):
                st.error("No database exists to backup yet.")
            else:
                try:
                    # Create ZIP in memory
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as z:
                        z.write(DATA_FILE, arcname="melmar_database_backup.json")
                    zip_buffer.seek(0)

                    # Create Email
                    msg = EmailMessage()
                    msg['Subject'] = f'Farmacia Melmar Database Backup - {datetime.today().date()}'
                    msg['From'] = sender_email
                    msg['To'] = receiver_email
                    msg.set_content("Attached is the compressed ZIP file containing your offline Med Sync database backup.")
                    
                    msg.add_attachment(zip_buffer.read(), maintype='application', subtype='zip', filename=f"Melmar_Backup_{datetime.today().date()}.zip")
                    
                    # Send Email via Gmail SMTP
                    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                        smtp.login(sender_email, email_password)
                        smtp.send_message(msg)
                        
                    st.success("✅ ZIP Backup successfully emailed!")
                except Exception as e:
                    st.error(f"Failed to send email. Check your App Password. Error: {e}")