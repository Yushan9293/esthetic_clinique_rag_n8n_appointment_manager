from datetime import datetime, timedelta, time
import pytz
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os
from dotenv import load_dotenv

load_dotenv()
DOCTOR_A_CALENDAR_ID = os.getenv("DOCTOR_A_CALENDAR_ID")
DOCTOR_B_CALENDAR_ID = os.getenv("DOCTOR_B_CALENDAR_ID")
credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH")

# ✅ 1. Doctor calendar mapping
DOCTORS = {
    "Dr A": DOCTOR_A_CALENDAR_ID,
    "Dr B": DOCTOR_B_CALENDAR_ID
}

# ✅ 2. Working hours configuration (customizable)
WORK_HOURS = {
    "start": time(9, 0),   # 09:00 AM
    "end": time(17, 0)     # 05:00 PM
}

# ✅ 3. Load Google Calendar API credentials
def get_google_calendar_service():
    credentials = service_account.Credentials.from_service_account_file(
        credentials_path,  # 🔁 Replace with your actual credentials file path
        scopes=["https://www.googleapis.com/auth/calendar"]
    )
    return build("calendar", "v3", credentials=credentials)

# ✅ 4. Fetch available time slots for a given doctor and date (excluding busy events)
def get_available_slots(doctor_name, date_str, duration_minutes):
    if doctor_name not in DOCTORS:
        raise ValueError(f"Unknown doctor: {doctor_name}")
    
    service = get_google_calendar_service()
    calendar_id = DOCTORS[doctor_name]

    # Parse date and define working hours range
    tz = pytz.timezone("Europe/Paris")
    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    start_datetime = tz.localize(datetime.combine(target_date, WORK_HOURS["start"]))
    end_datetime = tz.localize(datetime.combine(target_date, WORK_HOURS["end"]))

    # Fetch events already booked on the calendar
    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=start_datetime.isoformat(),
        timeMax=end_datetime.isoformat(),
        singleEvents=True,
        orderBy="startTime"
    ).execute()
    events = events_result.get("items", [])

    # Generate all possible time slots based on the treatment duration
    slot = timedelta(minutes=duration_minutes)
    current = start_datetime
    all_slots = []
    while current + slot <= end_datetime:
        all_slots.append((current, current + slot))
        current += slot

    # Extract booked/busy time ranges
    busy_slots = []
    for event in events:
        start = datetime.fromisoformat(event["start"]["dateTime"]).astimezone(tz)
        end = datetime.fromisoformat(event["end"]["dateTime"]).astimezone(tz)
        busy_slots.append((start, end))

    # Check whether a slot overlaps with any busy period
    def is_conflicting(start, end):
        for busy_start, busy_end in busy_slots:
            if start < busy_end and end > busy_start:
                return True
        return False

    # Return all available (non-conflicting) slots as string
    available_slots = []
    for start, end in all_slots:
        if not is_conflicting(start, end):
            available_slots.append(start.strftime("%Y-%m-%d %H:%M"))

    return available_slots

