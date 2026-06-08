import gspread
import json
import os

from google.oauth2.service_account import Credentials
from datetime import datetime

# ================= GOOGLE SHEETS =================

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Railway Environment Variable
creds_dict = json.loads(
    os.environ["GOOGLE_CREDENTIALS"]
)

creds = Credentials.from_service_account_info(
    creds_dict,
    scopes=SCOPES
)

client = gspread.authorize(creds)

# Google Sheet Name
sheet = client.open("hospital_db")

# Worksheets
doctors_sheet = sheet.worksheet("Doctors")
appointments_sheet = sheet.worksheet("Appointments")

# ================= HELPERS =================

def now():
    return datetime.utcnow().isoformat()


def next_id(sheet_obj):

    records = sheet_obj.get_all_records()

    if not records:
        return 1

    ids = []

    for r in records:

        try:
            ids.append(int(r.get("id", 0)))

        except:
            pass

    return max(ids) + 1 if ids else 1

# ================= DOCTORS =================

def get_doctors():

    return doctors_sheet.get_all_records()


def add_doctor(data):

    doctors_sheet.append_row([
        next_id(doctors_sheet),
        data.get("name", ""),
        data.get("specialty", ""),
        data.get("days", ""),
        data.get("start_time", ""),
        data.get("end_time", ""),
        data.get("fee", ""),
        now()
    ])


def delete_doctor(name):

    rows = doctors_sheet.get_all_records()

    for i, r in enumerate(rows):

        if r.get("name") == name:

            doctors_sheet.delete_rows(i + 2)

            return True

    return False

# ================= APPOINTMENTS =================

def get_appointments():

    return appointments_sheet.get_all_records()


def add_appointment(data):

    print("ADDING APPOINTMENT:", data)

    appointments_sheet.append_row([
        next_id(appointments_sheet),
        data.get("patient_name", ""),
        data.get("phone", ""),
        data.get("reason", ""),
        data.get("doctor", ""),
        data.get("date", ""),
        data.get("time", ""),
        "Booked",
        now()
    ])

    print("APPOINTMENT SAVED")


def cancel_appointment(name, phone):

    rows = appointments_sheet.get_all_records()

    for i, r in enumerate(rows):

        if (
            r.get("patient_name") == name
            and r.get("phone") == phone
        ):

            appointments_sheet.update_cell(
                i + 2,
                8,
                "Cancelled"
            )

            return True

    return False


def reschedule_appointment(
    name,
    phone,
    new_date,
    new_time
):

    rows = appointments_sheet.get_all_records()

    for i, r in enumerate(rows):

        if (
            r.get("patient_name") == name
            and r.get("phone") == phone
        ):

            appointments_sheet.update_cell(
                i + 2,
                6,
                new_date
            )

            appointments_sheet.update_cell(
                i + 2,
                7,
                new_time
            )

            appointments_sheet.update_cell(
                i + 2,
                8,
                "Rescheduled"
            )

            return True

    return False
