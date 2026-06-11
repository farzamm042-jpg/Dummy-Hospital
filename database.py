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

creds_dict = json.loads(
    os.environ["GOOGLE_CREDENTIALS"]
)

creds = Credentials.from_service_account_info(
    creds_dict,
    scopes=SCOPES
)

client = gspread.authorize(creds)

sheet = client.open("hospital_db")

doctors_sheet = sheet.worksheet("Doctors")
appointments_sheet = sheet.worksheet("Appointments")

# ================= DOCTOR LEAVES =================

try:
    leaves_sheet = sheet.worksheet("DoctorLeaves")
except:
    leaves_sheet = None

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


# ================= NORMALIZATION (IMPORTANT FIX) =================

def normalize_time(time_str):
    """
    Converts:
    - 9am, 9 AM, 09:00 AM → 09:00
    """
    try:
        if not time_str:
            return ""

        t = str(time_str).strip().lower()

        # AM/PM format
        if "am" in t or "pm" in t:
            dt = datetime.strptime(t.upper(), "%I:%M %p")
            return dt.strftime("%H:%M")

        # already 24-hour format
        if ":" in t:
            dt = datetime.strptime(t, "%H:%M")
            return dt.strftime("%H:%M")

        return t

    except:
        return str(time_str).strip().lower()


def normalize_name(name):
    return str(name).strip().lower()


def normalize_date(date):
    return str(date).strip()


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
        if normalize_name(r.get("name")) == normalize_name(name):
            doctors_sheet.delete_rows(i + 2)
            return True

    return False


# ================= APPOINTMENTS =================

def get_appointments():
    return appointments_sheet.get_all_records()


def add_appointment(data):
    appointments_sheet.append_row([
        next_id(appointments_sheet),
        data.get("patient_name", ""),
        data.get("phone", ""),
        data.get("reason", ""),
        data.get("doctor", ""),
        data.get("date", ""),
        normalize_time(data.get("time", "")),  # FIX APPLIED
        "Booked",
        now()
    ])


def cancel_appointment(name, phone):
    rows = appointments_sheet.get_all_records()

    for i, r in enumerate(rows):
        if (
            normalize_name(r.get("patient_name")) == normalize_name(name)
            and str(r.get("phone", "")).strip() == str(phone).strip()
        ):
            appointments_sheet.update_cell(i + 2, 8, "Cancelled")
            return True

    return False


def reschedule_appointment(name, phone, new_date, new_time):
    rows = appointments_sheet.get_all_records()

    for i, r in enumerate(rows):
        if (
            normalize_name(r.get("patient_name")) == normalize_name(name)
            and str(r.get("phone", "")).strip() == str(phone).strip()
        ):
            appointments_sheet.update_cell(i + 2, 6, new_date)
            appointments_sheet.update_cell(i + 2, 7, normalize_time(new_time))
            appointments_sheet.update_cell(i + 2, 8, "Rescheduled")
            return True

    return False


# ================= AVAILABILITY =================

def check_availability(doctor, date):
    appointments = appointments_sheet.get_all_records()

    booked = []

    for a in appointments:
        if (
            str(a.get("doctor", "")).strip() == str(doctor).strip()
            and normalize_date(a.get("date")) == normalize_date(date)
            and a.get("status") in ["Booked", "Rescheduled"]
        ):
            booked.append(normalize_time(a.get("time")))

    return booked


def is_slot_available(doctor, date, time):
    booked = check_availability(doctor, date)

    return normalize_time(time) not in booked


# ================= DOCTOR LEAVES =================

def is_doctor_on_leave(doctor, date):

    if not leaves_sheet:
        return False

    try:
        leaves = leaves_sheet.get_all_records()

        for leave in leaves:
            if (
                normalize_name(leave.get("doctor", "")) == normalize_name(doctor)
                and normalize_date(leave.get("date", "")) == normalize_date(date)
            ):
                return True

    except:
        return False

    return False
