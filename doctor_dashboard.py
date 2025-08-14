import streamlit as st
from datetime import datetime, timedelta
import gspread
from google.oauth2 import service_account
from googleapiclient.discovery import build
import pytz
import numpy as np
import json
import requests
import os
from dotenv import load_dotenv

load_dotenv()
N8N_WEBHOOK_MANAGE = os.getenv("WEBHOOK_MANAGE")
DOCTOR_A_CALENDAR_ID = os.getenv("DOCTOR_A_CALENDAR_ID")
DOCTOR_B_CALENDAR_ID = os.getenv("DOCTOR_B_CALENDAR_ID")
CREDS_FILE = os.getenv("GOOGLE_CREDENTIALS_PATH")

# Business utils
from backend.calendar_utils import get_available_slots

# Configuration
DOCTORS = {
    "Dr A": DOCTOR_A_CALENDAR_ID,
    "Dr B": DOCTOR_B_CALENDAR_ID,
}

with open("data/aesthetic_treatments_final.json", "r", encoding="utf-8") as f:
    TREATMENTS = json.load(f)

FALLBACK_DURATION = {
    "Consultation": 20,
    "Follow-up": 15,
}

def get_duration(service_name: str) -> int:
    for t in TREATMENTS:
        if t["treatment"].lower() == service_name.lower():
            return int(t.get("duration", 30))
    return int(FALLBACK_DURATION.get(service_name, 30))

# Google API helpers
def get_google_calendar_service():
    credentials = service_account.Credentials.from_service_account_file(
        CREDS_FILE,
        scopes=["https://www.googleapis.com/auth/calendar"],
    )
    return build("calendar", "v3", credentials=credentials)

def get_google_sheet_client():
    credentials = service_account.Credentials.from_service_account_file(
       CREDS_FILE,
        scopes=[
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    return gspread.authorize(credentials)

# Load appointments for a specific doctor and date
def fetch_appointments(doctor: str, date):
    calendar_id = DOCTORS.get(doctor)
    if not calendar_id:
        return []

    service = get_google_calendar_service()
    tz = pytz.timezone("Europe/Paris")
    day_start = tz.localize(datetime.combine(date, datetime.min.time()))
    day_end = tz.localize(datetime.combine(date, datetime.max.time()))

    events_result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=day_start.isoformat(),
            timeMax=day_end.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    return events_result.get("items", [])

# Get patient info from Google Sheets based on event ID
def get_patient_info(event_id: str):
    try:
        sheet = (
            get_google_sheet_client()
            .open("Aesthetic_clinique")
            .worksheet("clients_info")
        )
        records = sheet.get_all_records()
        
        print("🔍 Looking for event ID in Google Sheet:", event_id)

        for row in records:
            row_event_id = str(row.get("eventId") or "").strip()
            
            # Debug print to help compare what's in the sheet
            print("👀 Row eventId:", row_event_id)

            if row_event_id and row_event_id == str(event_id).strip():
                return {
                    "Name": safe_str(row.get("name", "")),
                    "Phone": safe_str(row.get("phone", "")),
                    "Age": safe_str(row.get("age", "")),
                    "Email": safe_str(row.get("email", "")),
                    "Event ID": safe_str(row_event_id),
                    "Time": safe_str(str(row.get("date", "")).split(" ")[-1][:5]),
                    "Service": safe_str(row.get("service", "")),
                    "Doctor": safe_str(row.get("doctor", "")),
                    "Booking ID": safe_str(row.get("booking_id", ""))
                }

    except Exception as e:
        print("Error in get_patient_info:", e)

    return {"Name": "", "Phone": "", "Age": "", "Email": "", "Event ID": "", "Time": "", "Service": "", "Doctor": ""}

# Helper to safely convert values to string
def safe_str(value):
    if isinstance(value, (list, tuple)):
        return ", ".join(map(str, value))
    if isinstance(value, np.ndarray):
        return ", ".join(map(str, value.tolist()))
    if hasattr(value, "tolist"):
        return str(value.tolist())
    return str(value) if value is not None else ""

# --- Streamlit App ---
st.set_page_config(page_title="Doctor Calendar Dashboard", layout="wide")
st.title("🗕️ Doctor Booking Overview")

if "editing_row" not in st.session_state:
    st.session_state.editing_row = None

sel_doctor = st.selectbox("👩‍⚕️ Select Doctor", list(DOCTORS.keys()))
sel_date = st.date_input("🗕️ Select Date", value=datetime.today().date())

appointments = fetch_appointments(sel_doctor, sel_date)
rows = []
for ev in appointments:
    try:
        start_time = ev.get("start", {}).get("dateTime", "")
        if not start_time:
            continue
        time_str = start_time[11:16]
        event_id = ev.get("id", "")
        p = get_patient_info(event_id)
        rows.append({
            "Time": safe_str(time_str),
            "Name": p.get("Name", ""),
            "Email": p.get("Email", ""),
            "Phone": p.get("Phone", ""),
            "Service": p.get("Service", ""),
            "Age": p.get("Age", ""),
            "Event ID": event_id,
            "Doctor": p.get("Doctor", sel_doctor) or sel_doctor,
            "Booking ID": p.get("Booking ID", ""),
        })
        print("Event time:", time_str, "| Event ID:", event_id)
        print("Searching for Event ID in Sheet:", event_id)

    except Exception as e:
        print("[parse error]", e)

if not rows:
    st.warning("⚠️ No appointments found for the selected doctor and date.")
    st.stop()

st.success("✅ Appointments loaded successfully!")

# Table rendering
headers = ["Time", "Name", "Email", "Phone", "Service", "Age", "Event ID"]
cols = st.columns([1, 1.1, 2, 1.2, 1.2, 0.6, 2, 2])
for c, h in zip(cols[:-1], headers):
    c.markdown(f"**{h}**")
cols[-1].markdown("**Actions**")

for i, r in enumerate(rows):
    c_time, c_name, c_email, c_phone, c_service, c_age, c_eid, c_actions = st.columns([1, 1.1, 2, 1.2, 1.2, 0.6, 2, 2])
    c_time.write(r["Time"])
    c_name.write(r["Name"])
    c_email.write(f"[{r['Email']}](mailto:{r['Email']})")
    c_phone.write(r["Phone"])
    c_service.write(r["Service"])
    c_age.write(r["Age"])
    c_eid.code(r["Event ID"], language="text")

    b1, b2 = c_actions.columns([1, 1])
    if b1.button("✏️ Edit", key=f"edit_{i}", help="Reschedule this appointment", use_container_width=True):
        st.session_state.editing_row = i
    if b2.button("❌ Cancel", key=f"cancel_{i}", help="Cancel this appointment", use_container_width=True):
        payload = {
            "action": "cancel",
            "event_id": r["Event ID"],
            "name": r["Name"],
            "email": r["Email"],
            "doctor": r["Doctor"],
            "date": sel_date.strftime("%Y-%m-%d"),
            "time": r["Time"],
            "service": r["Service"],
            "booking_id": r["Booking ID"]
        }
        try:
            res = requests.post(N8N_WEBHOOK_MANAGE, json=payload, timeout=20)
            if res.status_code == 200:
                st.success("🗑️ Appointment successfully cancelled.")
            else:
                st.error(f"❌ Failed to cancel appointment. HTTP {res.status_code}")
        except Exception as e:
            st.error(f"❌ Failed to cancel appointment: {e}")

# Edit and reschedule section
idx = st.session_state.editing_row
if idx is not None and 0 <= idx < len(rows):
    row = rows[idx]
    st.markdown("---")
    st.subheader(f"🔁 Reschedule: {row['Name']} — {row['Time']} ({row['Service']})")

    # Store session state variables
    if "reschedule_doctor" not in st.session_state:
        st.session_state.reschedule_doctor = row["Doctor"]
    if "reschedule_date" not in st.session_state:
        st.session_state.reschedule_date = sel_date
    if "reschedule_treatment" not in st.session_state:
        st.session_state.reschedule_treatment = row["Service"]

    new_doctor = st.selectbox("👩‍⚕️ Select doctor", list(DOCTORS.keys()), index=list(DOCTORS.keys()).index(st.session_state.reschedule_doctor), key="reschedule_doctor")
    new_date = st.date_input("📅 New date", value=st.session_state.reschedule_date, min_value=datetime.today().date(), key="reschedule_date")

    treatment_options = ["Consultation"] + [t["treatment"] for t in TREATMENTS]
    treatment = st.selectbox("💆 Treatment", options=treatment_options, index=(treatment_options.index(st.session_state.reschedule_treatment) if st.session_state.reschedule_treatment in treatment_options else 0), key="reschedule_treatment")

    # Dynamically update available time slots
    duration = get_duration(treatment)
    slots = get_available_slots(new_doctor, new_date.strftime("%Y-%m-%d"), duration)
    time_slot = st.selectbox("⏰ Available time", slots if slots else ["No available slots"])

    if st.button("✅ Submit Reschedule"):
        if not slots or time_slot == "No available slots":
            st.error("Please pick a valid time slot.")
        else:
            start_dt = datetime.strptime(f"{new_date.strftime('%Y-%m-%d')} {time_slot[-5:]}", "%Y-%m-%d %H:%M")
            end_dt = start_dt + timedelta(minutes=duration)
            tz_paris = pytz.timezone("Europe/Paris")
            start_dt = tz_paris.localize(start_dt)
            end_dt = tz_paris.localize(end_dt)

            start_time_str = start_dt.astimezone(pytz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            end_time_str = end_dt.astimezone(pytz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            payload = {
                "action": "reschedule",
                "event_id": row["Event ID"],
                "email": row["Email"],
                "name": row["Name"],
                "phone": row["Phone"],
                "age": row["Age"],
                "old_date": sel_date.strftime("%Y-%m-%d"),
                "old_time": row["Time"],
                "new_date": new_date.strftime("%Y-%m-%d"),
                "new_time": time_slot,
                "old_doctor": row["Doctor"],
                "doctor": new_doctor,
                "duration": duration,
                "service": treatment,
                "start_time": start_time_str,
                "end_time": end_time_str,
                "booking_id": row["Booking ID"],
            }

            try:
                res = requests.post(N8N_WEBHOOK_MANAGE, json=payload, timeout=20)
                if res.status_code == 200:
                    st.success("✅ Appointment successfully rescheduled.")
                    st.session_state.editing_row = None
                else:
                    st.error(f"❌ Failed to reschedule. HTTP {res.status_code}")
            except Exception as e:
                st.error(f"❌ Failed to reschedule: {e}")

# Exit edit mode
if st.session_state.editing_row is not None:
    if st.button("Done", type="secondary"):
        st.session_state.editing_row = None

