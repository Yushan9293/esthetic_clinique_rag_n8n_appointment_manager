import streamlit as st
import requests
import gspread
import uuid
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
from backend.calendar_utils import get_available_slots
import json
import pytz
import os
from dotenv import load_dotenv

load_dotenv()
N8N_WEBHOOK_MANAGE = os.getenv("WEBHOOK_MANAGE")
credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH")

# Load treatment data
with open("data/aesthetic_treatments_final.json", "r", encoding="utf-8") as f:
    treatment_data_list = json.load(f)

fallback_duration = {
    "Consultation": 20,
    "Follow-up": 15
}

def get_duration(service_name):
    for treatment in treatment_data_list:
        if treatment["treatment"].lower() == service_name.lower():
            return treatment.get("duration", 30)
    return fallback_duration.get(service_name, 30)

st.set_page_config(page_title="📅 Manage Appointment")
st.title("📋 Manage Your Appointment")

# --- Load query parameters ---
query_params = st.query_params
prefilled_event_id = query_params.get("event_id", "")
booking_id = query_params.get("booking_id")
if not booking_id:
    st.error("❌ Missing booking ID. Please use the correct appointment link.")
    st.stop()

# --- Load appointment from Google Sheets ---
def get_appointment_by_booking_id(booking_id):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        credentials_path, scope)
    client = gspread.authorize(creds)

    sheet = client.open("Aesthetic_clinique").worksheet("clients_info")
    data = sheet.get_all_records()

    for row in data:
        if str(row.get("booking_id", "")).strip() == str(booking_id).strip():
            return row
    return {}

appointment = get_appointment_by_booking_id(booking_id) if booking_id else {}
old_doctor = appointment.get("doctor", "")
email = appointment.get("email", "")
name = appointment.get("name", "")
phone = appointment.get("phone", "")
age = appointment.get("age", "")
event_id = appointment.get("eventId", prefilled_event_id)

# --- Form Fields ---
st.markdown("Please fill in the details below to manage your appointment:")

email = st.text_input("📧 Your email", value=email)
st.text_input("🆔 Booking ID (do not edit)", value=booking_id, disabled=True)
st.text_input("📌 Google Calendar Event ID", value=event_id, disabled=True)

# ✅ Show original doctor & service
original_doctor = appointment.get("doctor", "")
original_service = appointment.get("service", "")
st.text_input("👩‍⚕️ Original doctor", value=original_doctor, disabled=True)
st.text_input("💆 Original service", value=original_service, disabled=True)

# Parse original appointment date & time
if appointment and "date" in appointment:
    try:
        dt = datetime.strptime(appointment["date"], "%Y-%m-%d %H:%M")
        parsed_date = dt.date()
        parsed_time = dt.time()
    except ValueError:
        parsed_date = datetime.today().date()
        parsed_time = datetime.now().time()
else:
    parsed_date = datetime.today().date()
    parsed_time = datetime.now().time()

original_date = st.date_input("📅 Original appointment date", value=parsed_date)
original_time = st.time_input("🕒 Original appointment time", value=parsed_time)

st.divider()

# --- Action Selection ---
action = st.radio("What would you like to do?", ["Cancel Appointment", "Reschedule Appointment"])

# --- Cancel Appointment ---
if action == "Cancel Appointment":
    if st.button("❌ Cancel Appointment"):
        service = appointment.get("service", "")
        date_str = appointment.get("date", "")
        time_str = appointment.get("time", "")

        # fallback to UI input if sheet info missing
        try:
            parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except:
            parsed_date = original_date
        try:
            parsed_time = datetime.strptime(time_str, "%H:%M").time()
        except:
            parsed_time = original_time

        payload = {
            "action": "cancel",
            "booking_id": booking_id,
            "event_id": event_id,
            "name": name,
            "email": email,
            "doctor": old_doctor,
            "date": parsed_date.strftime("%Y-%m-%d"),
            "time": parsed_time.strftime("%H:%M"),
            "service": service
        }

        res = requests.post(N8N_WEBHOOK_MANAGE , json=payload)
        if res.status_code == 200:
            st.success("✅ Appointment successfully cancelled.")
        else:
            st.error("❌ Failed to cancel appointment.")


# --- Reschedule Appointment ---
if action == "Reschedule Appointment":
    doctor = st.selectbox("👩‍⚕️ Select a doctor", ["Dr A", "Dr B"])
    new_date = st.date_input("📅 Select a new date", min_value=datetime.today().date())

    treatment_options = ["Consultation"] + [t["treatment"] for t in treatment_data_list]
    treatment = st.selectbox("💆 Select a treatment", options=treatment_options)
    duration = get_duration(treatment)

    slots = get_available_slots(doctor, new_date.strftime("%Y-%m-%d"), duration)
    if slots:
        time_slot = st.selectbox("⏰ Select a time slot", slots)
    else:
        time_slot = None
        st.warning("⚠️ No available slots for this date.")

    if st.button("🔁 Reschedule Appointment"):
        if not time_slot:
            st.error("Please select a valid time.")
        else:
            start_dt = datetime.strptime(f"{new_date.strftime('%Y-%m-%d')} {time_slot[-5:]}", "%Y-%m-%d %H:%M")
            end_dt = start_dt + timedelta(minutes=duration)
            
            # Set Paris timezone
            tz_paris = pytz.timezone("Europe/Paris")
            start_dt = tz_paris.localize(start_dt)
            end_dt = tz_paris.localize(end_dt)

            # Convert to UTC for n8n payload
            start_time_str = start_dt.astimezone(pytz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            end_time_str = end_dt.astimezone(pytz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            payload = {
                "action": "reschedule",
                "booking_id": booking_id,
                "event_id": event_id,
                "email": email,
                "name": name,
                "phone": phone,
                "age": age,
                "old_date": original_date.strftime("%Y-%m-%d"),
                "old_time": original_time.strftime("%H:%M"),
                "new_date": new_date.strftime("%Y-%m-%d"),
                "new_time": time_slot,
                "old_doctor": old_doctor,
                "doctor": doctor,
                "duration": duration,
                "service": treatment,
                "start_time": start_time_str,
                "end_time": end_time_str
            }
            res = requests.post(N8N_WEBHOOK_MANAGE, json=payload)
            if res.status_code == 200:
                st.success("✅ Appointment successfully rescheduled.")
            else:
                st.error("❌ Failed to reschedule appointment.")
