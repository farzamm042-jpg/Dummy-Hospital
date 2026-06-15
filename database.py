import gspread
import json
import os
import re
from google.oauth2.service_account import Credentials
from datetime import datetime, date

# ================= GOOGLE SHEETS =================
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
if creds_json:
    creds_dict = json.loads(creds_json)
else:
    with open("credentials.json") as f:
        creds_dict = json.load(f)

creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
client = gspread.authorize(creds)

SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "your_spreadsheet_id_here")
spreadsheet = client.open_by_key(SPREADSHEET_ID)
doctors_sheet = spreadsheet.worksheet("Doctors")
appointments_sheet = spreadsheet.worksheet("Appointments")


# ================= NAME NORMALIZATION =================

NAME_VARIANTS = {
    "mohammad": ["mohammed", "muhammad", "mohd", "md", "mohamad", "muhammed"],
    "mohammed": ["mohammad", "muhammad", "mohd", "md", "mohamad", "muhammed"],
    "muhammad": ["mohammad", "mohammed", "mohd", "md", "mohamad", "muhammed"],
    "mohd":     ["mohammad", "mohammed", "muhammad", "md", "mohamad"],
    "mohamad":  ["mohammad", "mohammed", "muhammad"],
    "muhammed": ["mohammad", "mohammed", "muhammad"],
    "hassan":   ["hasan"],
    "hasan":    ["hassan"],
    "hussain":  ["hussein", "husain", "husein"],
    "hussein":  ["hussain", "husain", "husein"],
    "usman":    ["uthman", "osman"],
    "uthman":   ["usman", "osman"],
    "fatima":   ["fatimah", "fatemah"],
    "fatimah":  ["fatima", "fatemah"],
    "ayesha":   ["aisha", "aysha", "aiesha"],
    "aisha":    ["ayesha", "aysha"],
    "ali":      ["aly"],
    "bilal":    ["bilaal"],
    "omar":     ["umar", "umer"],
    "umar":     ["omar", "umer"],
}

def normalize_name(name: str) -> str:
    return name.strip().lower()

def expand_words(words: list) -> set:
    expanded = set(words)
    for w in words:
        if w in NAME_VARIANTS:
            expanded.update(NAME_VARIANTS[w])
    return expanded

def names_match(name1: str, name2: str) -> bool:
    """
    Fuzzy name match — handles Pakistani/Arabic name spelling variations.
    - Full names: last word (surname) must match exactly, first name fuzzy matched.
    - Single word names: any overlap is enough.
    """
    n1_words = normalize_name(name1).split()
    n2_words = normalize_name(name2).split()

    if not n1_words or not n2_words:
        return False

    if len(n1_words) == 1 or len(n2_words) == 1:
        set1 = expand_words(n1_words)
        set2 = expand_words(n2_words)
        return bool(set1 & set2)

    # Full names — last name must match exactly
    if n1_words[-1] != n2_words[-1]:
        return False

    # First names — fuzzy match with variants
    first1 = expand_words(n1_words[:-1])
    first2 = expand_words(n2_words[:-1])
    return bool(first1 & first2)


# ================= TIME NORMALIZATION =================

def normalize_time(time_str: str) -> str:
    """Convert any time format to HH:MM 24h for storage."""
    if not time_str:
        return time_str
    time_str = str(time_str).strip().upper()

    # Already HH:MM 24h
    if re.match(r'^\d{1,2}:\d{2}$', time_str):
        h, m = time_str.split(":")
        return f"{int(h):02d}:{int(m):02d}"

    # 12h format: 7:00 PM, 07:00 PM, 7 PM
    match = re.match(r'^(\d{1,2})(?::(\d{2}))?\s*(AM|PM)$', time_str)
    if match:
        h = int(match.group(1))
        m = int(match.group(2) or 0)
        period = match.group(3)
        if period == "PM" and h != 12:
            h += 12
        elif period == "AM" and h == 12:
            h = 0
        return f"{h:02d}:{m:02d}"

    return time_str


# ================= DAY OF WEEK =================

DAY_MAP = {
    "monday": 0, "mon": 0,
    "tuesday": 1, "tue": 1, "tues": 1,
    "wednesday": 2, "wed": 2,
    "thursday": 3, "thu": 3, "thur": 3, "thurs": 3,
    "friday": 4, "fri": 4,
    "saturday": 5, "sat": 5,
    "sunday": 6, "sun": 6,
}

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def get_day_name(date_str: str) -> str:
    """Return day name (e.g. 'Monday') for a YYYY-MM-DD string."""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        return DAY_NAMES[d.weekday()]
    except Exception:
        return "Unknown"


def parse_doctor_days(days_str: str) -> set:
    """
    Parse doctor working days string into a set of weekday integers (0=Mon, 6=Sun).
    Handles: Daily, Monday to Saturday, Mon-Wed, Tuesday to Saturday, etc.
    """
    if not days_str:
        return set(range(7))

    s = days_str.strip().lower()

    if s == "daily":
        return set(range(7))

    # "Monday to Saturday" or "Mon-Wed"
    sep_match = re.match(r'(\w+)\s+to\s+(\w+)', s) or re.match(r'(\w+)-(\w+)', s)
    if sep_match:
        start_word = sep_match.group(1)
        end_word = sep_match.group(2)
        start = DAY_MAP.get(start_word)
        end = DAY_MAP.get(end_word)
        if start is not None and end is not None:
            if start <= end:
                return set(range(start, end + 1))
            else:
                return set(range(start, 7)) | set(range(0, end + 1))

    if s in DAY_MAP:
        return {DAY_MAP[s]}

    result = set()
    for part in re.split(r'[,/]', s):
        part = part.strip()
        if part in DAY_MAP:
            result.add(DAY_MAP[part])
    if result:
        return result

    return set(range(7))


def is_doctor_working_on_date(doctor_row_or_days, check_date: str) -> bool:
    """
    Returns True if doctor works on the given date.
    Accepts either a doctor dict (row) or a days string directly.
    check_date format: YYYY-MM-DD
    """
    try:
        if isinstance(doctor_row_or_days, dict):
            days_str = doctor_row_or_days.get("days", "")
        else:
            days_str = str(doctor_row_or_days)

        d = datetime.strptime(check_date, "%Y-%m-%d").date()
        weekday = d.weekday()
        working_days = parse_doctor_days(days_str)
        return weekday in working_days
    except Exception:
        return True


def is_doctor_on_leave(doctor_name: str, check_date: str) -> bool:
    """
    Returns True if doctor is on leave on given date.
    Leave is stored as status='Leave' in appointments sheet with the doctor's name.
    """
    try:
        rows = appointments_sheet.get_all_records()
        for r in rows:
            if (
                normalize_name(r.get("doctor", "")) == normalize_name(doctor_name)
                and r.get("date", "") == check_date
                and r.get("status", "") == "Leave"
            ):
                return True
    except Exception:
        pass
    return False


def is_slot_available(doctor_name: str, check_date: str, time_24h: str) -> bool:
    """
    Returns True if the given slot is NOT already booked for this doctor/date.
    time_24h should be in HH:MM format.
    """
    try:
        rows = appointments_sheet.get_all_records()
        for r in rows:
            if (
                normalize_name(r.get("doctor", "")) == normalize_name(doctor_name)
                and r.get("date", "") == check_date
                and normalize_time(r.get("time", "")) == normalize_time(time_24h)
                and r.get("status", "") not in ["Cancelled"]
            ):
                return False  # Slot is taken
        return True  # Slot is free
    except Exception:
        return True


# ================= DOCTORS =================

def get_doctors():
    rows = doctors_sheet.get_all_records()
    result = []
    for i, r in enumerate(rows):
        result.append({
            "id": i + 1,
            "name": r.get("name", ""),
            "specialty": r.get("specialty", ""),
            "days": r.get("days", ""),
            "start_time": r.get("start_time", ""),
            "end_time": r.get("end_time", ""),
            "fee": r.get("fee", ""),
            "timestamp": r.get("timestamp", ""),
        })
    return result


def add_doctor(name, specialty, days, start_time, end_time, fee):
    timestamp = datetime.now().isoformat()
    doctors_sheet.append_row([name, specialty, days, start_time, end_time, fee, timestamp])
    return True


def delete_doctor(name):
    rows = doctors_sheet.get_all_records()
    for i, r in enumerate(rows):
        if normalize_name(r.get("name", "")) == normalize_name(name):
            doctors_sheet.delete_rows(i + 2)
            return True
    return False


def get_doctor_row_by_name(name: str):
    """Return full doctor row dict or None."""
    rows = doctors_sheet.get_all_records()
    for r in rows:
        if normalize_name(r.get("name", "")) == normalize_name(name):
            return r
    return None


# ================= APPOINTMENTS =================

def get_appointments():
    rows = appointments_sheet.get_all_records()
    result = []
    for i, r in enumerate(rows):
        result.append({
            "id": i + 1,
            "patient_name": r.get("patient_name", ""),
            "phone": r.get("phone", ""),
            "reason": r.get("reason", ""),
            "doctor": r.get("doctor", ""),
            "date": r.get("date", ""),
            "time": r.get("time", ""),
            "status": r.get("status", ""),
            "timestamp": r.get("timestamp", ""),
        })
    return result


def add_appointment(patient_name, phone, reason, doctor, appt_date, appt_time):
    timestamp = datetime.now().isoformat()
    normalized_time = normalize_time(appt_time)
    appointments_sheet.append_row([
        patient_name, phone, reason, doctor,
        appt_date, normalized_time, "Booked", timestamp
    ])
    return True


def cancel_appointment(name, phone):
    """
    Cancel — match by phone (primary) + fuzzy name (secondary).
    """
    rows = appointments_sheet.get_all_records()
    for i, r in enumerate(rows):
        phone_match = str(r.get("phone", "")).strip() == str(phone).strip()
        name_ok = names_match(r.get("patient_name", ""), name)
        status_ok = r.get("status", "") not in ["Cancelled"]

        if phone_match and name_ok and status_ok:
            appointments_sheet.update_cell(i + 2, 7, "Cancelled")
            return True
    return False


def reschedule_appointment(name, phone, new_date, new_time):
    """
    Reschedule — match by phone (primary) + fuzzy name (secondary).
    """
    rows = appointments_sheet.get_all_records()
    normalized_time = normalize_time(new_time)
    for i, r in enumerate(rows):
        phone_match = str(r.get("phone", "")).strip() == str(phone).strip()
        name_ok = names_match(r.get("patient_name", ""), name)
        status_ok = r.get("status", "") not in ["Cancelled"]

        if phone_match and name_ok and status_ok:
            appointments_sheet.update_cell(i + 2, 5, new_date)
            appointments_sheet.update_cell(i + 2, 6, normalized_time)
            appointments_sheet.update_cell(i + 2, 7, "Rescheduled")
            return True
    return False


# ================= AVAILABILITY CHECK =================

def check_availability(doctor_name: str, check_date: str):
    """
    Returns set of booked time slots (HH:MM 24h) for a doctor on given date.
    Used internally by backend for slot filtering.
    """
    booked = set()
    try:
        rows = appointments_sheet.get_all_records()
        for r in rows:
            if (
                normalize_name(r.get("doctor", "")) == normalize_name(doctor_name)
                and r.get("date", "") == check_date
                and r.get("status", "") not in ["Cancelled"]
            ):
                booked.add(normalize_time(r.get("time", "")))
    except Exception:
        pass
    return booked
