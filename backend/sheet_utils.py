from dotenv import load_dotenv
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

load_dotenv()

# Set up Google Sheets access
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
CREDS_FILE = os.getenv("GOOGLE_CREDENTIALS_PATH")

credentials = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, SCOPE)
client = gspread.authorize(credentials)

# Change this to your actual sheet name
def get_worksheet(sheet_name="Aesthetic_clinique", worksheet_name="clients_info"):
    sheet = client.open(sheet_name)
    return sheet.worksheet(worksheet_name)

def find_appointment_by_event_id(event_id):
    """
    Returns the first row (as a dict) matching the given event_id, or None if not found.
    """
    worksheet = get_worksheet()
    records = worksheet.get_all_records()

    for row in records:
        if str(row.get("eventId")) == str(event_id):
            return row
    return None

# Optional: get all rows

def get_all_appointments():
    worksheet = get_worksheet()
    return worksheet.get_all_records()
