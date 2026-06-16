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

creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON") or os.environ.get("GOOGLE_CREDENTIALS")
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
    n1_words = normalize_name(name1).split()
    n2_words = normalize_name(name2).split()

    if not n1_words or not n2_words:
        return False

    if len(n1_words) == 1 or len(n2_words) == 1:
        set1 = expand_words(n1_words)
        set2 = expand_words(n2_words)
        return bool(set1 & set2)

    if n1_words[-1] != n2_words[-1]:
        return False

    first1 = expand_words(n1_words[:-1])
    first2 = expand_words(n2_words[:-1])
    return bool(first1 & first2)


# ================= TIME NORMALIZATION =================

def normalize_time(time_str: str) -> str:
    if not time_str:
        return time_str
    time_str = str(time_str).strip().upper()

    if re.match(r'^\d{1,2}:\d{2}$', time_str):
        h, m = time_str.split(":")
        return f"{int(h):02d}:{int(m):02d}"

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
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        return DAY_NAMES[d.weekday()]
    except Exception:
        return "Unknown"


def parse_doctor_days(days_str: str) -> set:
    if not days_str:
        return set(range(7))

    s = days_str.strip().lower()

    if s == "daily":
        return set(range(7))

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
    try:
        rows = appointments_sheet.get_all_records()
        for r in rows:
            if (
                normalize_name(r.get("doctor", "")) == normalize_name(doctor_name)
                and r.get("date", "") == check_date
                and normalize_time(r.get("time", "")) == normalize_time(time_24h)
                and r.get("status", "") not in ["Cancelled"]
            ):
                return False
        return True
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
    existing_rows = appointments_sheet.get_all_values()
    next_id = len(existing_rows)
    appointments_sheet.append_row([
        next_id, patient_name, phone, reason, doctor,
        appt_date, normalized_time, "Booked", timestamp
    ])
    return True


def _find_target_row(name: str, phone: str):
    """
    Find the single best matching active appointment row index (0-based in records list).

    Priority:
    1. Phone + name both match → most recent (highest index)
    2. Phone matches + only ONE active record → cancel/reschedule it regardless of name
       (handles cases where AI sends slightly different name or empty string)

    Returns (row_index, record) or (None, None)
    """
    rows = appointments_sheet.get_all_records()
    phone_clean = str(phone).strip()

    # All active records for this phone
    active = [
        (i, r) for i, r in enumerate(rows)
        if str(r.get("phone", "")).strip() == phone_clean
        and r.get("status", "") not in ["Cancelled"]
    ]

    if not active:
        return None, None

    # If only one active record — use it directly (no name check needed)
    if len(active) == 1:
        return active[0]

    # Multiple active records — try name match first (most recent match wins)
    name_matched = [
        (i, r) for i, r in active
        if names_match(r.get("patient_name", ""), name)
    ]

    if name_matched:
        # Return the most recent name match (highest sheet row = last booked)
        return name_matched[-1]

    # Name match failed but multiple records exist.
    # As last resort: return the most recent active record.
    # This handles cases where AI sends wrong/empty name but caller confirmed phone.
    return active[-1]


def cancel_appointment(name: str, phone: str) -> bool:
    """
    Cancel the best matching active appointment.
    Sheet columns: id(1) patient_name(2) phone(3) reason(4) doctor(5) date(6) time(7) status(8) timestamp(9)
    """
    i, r = _find_target_row(name, phone)
    if i is None:
        return False
    appointments_sheet.update_cell(i + 2, 8, "Cancelled")
    return True


def reschedule_appointment(name: str, phone: str, new_date: str, new_time: str) -> bool:
    """
    Reschedule the best matching active appointment.
    Sheet columns: id(1) patient_name(2) phone(3) reason(4) doctor(5) date(6) time(7) status(8) timestamp(9)
    """
    i, r = _find_target_row(name, phone)
    if i is None:
        return False
    normalized_time = normalize_time(new_time)
    appointments_sheet.update_cell(i + 2, 6, new_date)
    appointments_sheet.update_cell(i + 2, 7, normalized_time)
    appointments_sheet.update_cell(i + 2, 8, "Rescheduled")
    return True


# ================= AVAILABILITY CHECK =================

def check_availability(doctor_name: str, check_date: str):
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
