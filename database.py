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
    Strategy:
    - If both names have 2+ words (full names), LAST WORD (surname) must match exactly,
      and at least one first-name word must match (with variants).
    - If either name is single word, any word overlap is enough.
    """
    n1_words = normalize_name(name1).split()
    n2_words = normalize_name(name2).split()

    if not n1_words or not n2_words:
        return False

    # Single word names — any overlap
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
    """Convert any time format to HH:MM for storage."""
    time_str = time_str.strip().upper()
    
    # Already in HH:MM 24h
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


# ================= DAY OF WEEK PARSING =================

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

def parse_doctor_days(days_str: str) -> set:
    """
    Parse doctor working days string into a set of weekday integers (0=Mon, 6=Sun).
    Handles: Daily, Monday to Saturday, Mon-wed, Tuesday to Saturday, etc.
    """
    if not days_str:
        return set(range(7))
    
    s = days_str.strip().lower()
    
    if s == "daily":
        return set(range(7))
    
    # "Monday to Saturday" or "Mon-wed" patterns
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
                # Wraps around (e.g., Friday to Tuesday)
                return set(range(start, 7)) | set(range(0, end + 1))
    
    # Single day
    if s in DAY_MAP:
        return {DAY_MAP[s]}
    
    # Comma-separated list
    result = set()
    for part in re.split(r'[,/]', s):
        part = part.strip()
        if part in DAY_MAP:
            result.add(DAY_MAP[part])
    if result:
        return result
    
    # Default: all days
    return set(range(7))


def is_doctor_working_on_date(doctor_days_str: str, check_date: str) -> tuple:
    """
    Returns (is_working: bool, day_name: str)
    check_date format: YYYY-MM-DD
    """
    try:
        d = datetime.strptime(check_date, "%Y-%m-%d").date()
        weekday = d.weekday()  # 0=Mon, 6=Sun
        working_days = parse_doctor_days(doctor_days_str)
        return (weekday in working_days), DAY_NAMES[weekday]
    except Exception:
        return True, "Unknown"


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
    Cancel appointment — match by phone (primary) + fuzzy name (secondary).
    Phone must match. Name fuzzy matched to prevent family member conflicts.
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
    Reschedule appointment — match by phone (primary) + fuzzy name (secondary).
    Phone must match. Name fuzzy matched to prevent family member conflicts.
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
    Check if doctor is available on given date and return open slots.
    Returns dict with: available, available_slots, day, message, day_check_failed
    """
    doctor = get_doctor_row_by_name(doctor_name)
    if not doctor:
        return {
            "success": False,
            "available": False,
            "message": f"Doctor '{doctor_name}' not found in system."
        }

    # Step 1 — Day of week check
    is_working, day_name = is_doctor_working_on_date(doctor.get("days", ""), check_date)
    if not is_working:
        return {
            "success": True,
            "available": False,
            "day_check_failed": True,
            "day": day_name,
            "date": check_date,
            "doctor": doctor.get("name", doctor_name),
            "working_days": doctor.get("days", ""),
            "message": (
                f"Doctor {doctor.get('name', doctor_name)} does not work on {day_name}s. "
                f"Working days: {doctor.get('days', 'N/A')}. "
                f"Please ask the patient to choose a different date."
            )
        }

    # Step 2 — Generate slots from doctor's actual hours
    try:
        start_dt = datetime.strptime(doctor.get("start_time", "09:00"), "%H:%M")
        end_dt = datetime.strptime(doctor.get("end_time", "17:00"), "%H:%M")
    except ValueError:
        start_dt = datetime.strptime("09:00", "%H:%M")
        end_dt = datetime.strptime("17:00", "%H:%M")

    all_slots = []
    current = start_dt
    while current < end_dt:
        all_slots.append(current.strftime("%I:%M %p"))
        current = current.replace(hour=current.hour + 1)

    # Step 3 — Remove already booked slots
    booked = set()
    rows = appointments_sheet.get_all_records()
    for r in rows:
        if (
            normalize_name(r.get("doctor", "")) == normalize_name(doctor_name)
            and r.get("date", "") == check_date
            and r.get("status", "") not in ["Cancelled"]
        ):
            booked.add(normalize_time(r.get("time", "")))

    available_slots = []
    for slot in all_slots:
        slot_normalized = normalize_time(slot)
        if slot_normalized not in booked:
            available_slots.append(slot)

    if not available_slots:
        return {
            "success": True,
            "available": False,
            "day_check_failed": False,
            "day": day_name,
            "date": check_date,
            "doctor": doctor.get("name", doctor_name),
            "message": f"No available slots for {doctor.get('name', doctor_name)} on {check_date} ({day_name}). All slots are booked."
        }

    return {
        "success": True,
        "available": True,
        "day_check_failed": False,
        "day": day_name,
        "date": check_date,
        "doctor": doctor.get("name", doctor_name),
        "available_slots": available_slots,
        "message": (
            f"Available slots for {doctor.get('name', doctor_name)} on "
            f"{check_date} ({day_name}): {', '.join(available_slots)}"
        )
    }
