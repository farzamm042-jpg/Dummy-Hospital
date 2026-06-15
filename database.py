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

try:
    leaves_sheet = sheet.worksheet("DoctorLeaves")
except Exception:
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
        except Exception:
            pass
    return max(ids) + 1 if ids else 1


# ================= NORMALIZATION =================

def normalize_time(time_str):
    """
    Converts any time input to HH:MM 24-hour format for DB storage.
    Handles: 9am, 9 AM, 09:00 AM, 09:00, 9:00 AM, etc.
    """
    try:
        if not time_str:
            return ""
        t = str(time_str).strip()
        t = re.sub(r'\s+', ' ', t).strip()
        upper = t.upper()

        for fmt in ["%I:%M %p", "%I:%M%p"]:
            try:
                dt = datetime.strptime(upper, fmt)
                return dt.strftime("%H:%M")
            except ValueError:
                pass

        for fmt in ["%I %p", "%I%p"]:
            try:
                dt = datetime.strptime(upper, fmt)
                return dt.strftime("%H:%M")
            except ValueError:
                pass

        if ":" in t and len(t) <= 5:
            try:
                dt = datetime.strptime(t, "%H:%M")
                return dt.strftime("%H:%M")
            except ValueError:
                pass

        return t.lower()
    except Exception:
        return str(time_str).strip().lower()


def normalize_name(name):
    return str(name).strip().lower()


def normalize_date(date_val):
    return str(date_val).strip()


# ================= FUZZY NAME MATCHING =================

# Common Arabic/Pakistani name spelling variants
NAME_VARIANTS = {
    "mohammad": ["mohammed", "muhammad", "mohd", "md", "mohamad"],
    "mohammed": ["mohammad", "muhammad", "mohd", "md", "mohamad"],
    "muhammad": ["mohammad", "mohammed", "mohd", "md", "mohamad"],
    "mohamad":  ["mohammad", "mohammed", "muhammad", "mohd"],
    "mohd":     ["mohammad", "mohammed", "muhammad", "md"],
    "ali":      ["aly"],
    "hassan":   ["hasan"],
    "hussain":  ["husain", "hussein", "husein"],
    "usman":    ["uthman", "osman"],
    "zainab":   ["zaynab", "zenab"],
    "fatima":   ["fatimah", "fateema"],
}

def _expand_name_words(words: list) -> set:
    expanded = set(words)
    for w in words:
        if w in NAME_VARIANTS:
            expanded.update(NAME_VARIANTS[w])
    return expanded

def names_match(name1: str, name2: str) -> bool:
    """
    Fuzzy name match — handles Mohammad/Mohammed/Muhammad variations.
    Returns True if at least one word overlaps between the two names
    (after expanding known variants).
    Phone number is the primary key — this is a secondary safety check.
    """
    if not name1 or not name2:
        return True  # if one is missing, skip name check

    words1 = _expand_name_words(normalize_name(name1).split())
    words2 = _expand_name_words(normalize_name(name2).split())

    return bool(words1 & words2)


# ================= DAY-OF-WEEK ENGINE =================

def _name_to_weekday(s: str):
    """Convert day name/abbreviation to int. 0=Monday, 6=Sunday."""
    s = s.strip().lower()
    days = [
        "monday", "tuesday", "wednesday",
        "thursday", "friday", "saturday", "sunday"
    ]
    for i, d in enumerate(days):
        if d.startswith(s[:3]):
            return i
    return None


def parse_doctor_days(days_str: str) -> set:
    """
    Parse working days string into set of weekday ints.
    Handles: Daily, Monday to Saturday, Tuesday to Saturday,
             Monday to Friday, Mon-wed, Mon-Wed,
             Monday, Wednesday, Friday (comma list)
    """
    s = days_str.strip().lower()

    if s == "daily":
        return set(range(7))

    # Range: "monday to saturday" or "mon-wed"
    range_match = re.match(r'(\w+)\s*(?:to|-)\s*(\w+)', s)
    if range_match:
        start = _name_to_weekday(range_match.group(1))
        end   = _name_to_weekday(range_match.group(2))
        if start is not None and end is not None:
            if end >= start:
                return set(range(start, end + 1))
            else:
                return set(list(range(start, 7)) + list(range(0, end + 1)))

    # Comma-separated
    parts = [p.strip() for p in s.split(",")]
    result = set()
    for p in parts:
        n = _name_to_weekday(p)
        if n is not None:
            result.add(n)
    if result:
        return result

    return set(range(7))  # fallback: all days


def is_doctor_working_on_date(doctor_row: dict, date_str: str) -> bool:
    """Returns True if doctor works on the weekday of date_str."""
    try:
        d = datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
        weekday = d.weekday()  # 0=Mon, 6=Sun
        working_days = parse_doctor_days(doctor_row.get("days", "Daily"))
        return weekday in working_days
    except Exception:
        return True  # fail open


def get_day_name(date_str: str) -> str:
    try:
        d = datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
        return d.strftime("%A")
    except Exception:
        return ""


# ================= DOCTORS =================

def get_doctors():
    return doctors_sheet.get_all_records()


def get_doctor_row_by_name(doctor_name: str):
    """Fetch a single doctor row by name."""
    for d in get_doctors():
        if normalize_name(d.get("name", "")) == normalize_name(doctor_name):
            return d
    return None


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
        if normalize_name(r.get("name", "")) == normalize_name(name):
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
        normalize_time(data.get("time", "")),
        "Booked",
        now()
    ])


def cancel_appointment(name, phone):
    """
    Match by phone (primary) + fuzzy name (secondary).
    Handles Mohammad/Mohammed spelling variations.
    """
    rows = appointments_sheet.get_all_records()
    for i, r in enumerate(rows):
        phone_match = str(r.get("phone", "")).strip() == str(phone).strip()
        name_ok     = names_match(r.get("patient_name", ""), name)
        not_cancelled = r.get("status", "") not in ["Cancelled"]

        if phone_match and name_ok and not_cancelled:
            appointments_sheet.update_cell(i + 2, 8, "Cancelled")
            return True
    return False


def reschedule_appointment(name, phone, new_date, new_time):
    """
    Match by phone (primary) + fuzzy name (secondary).
    Handles Mohammad/Mohammed spelling variations.
    """
    rows = appointments_sheet.get_all_records()
    for i, r in enumerate(rows):
        phone_match = str(r.get("phone", "")).strip() == str(phone).strip()
        name_ok     = names_match(r.get("patient_name", ""), name)
        not_cancelled = r.get("status", "") not in ["Cancelled"]

        if phone_match and name_ok and not_cancelled:
            appointments_sheet.update_cell(i + 2, 6, new_date)
            appointments_sheet.update_cell(i + 2, 7, normalize_time(new_time))
            appointments_sheet.update_cell(i + 2, 8, "Rescheduled")
            return True
    return False


# ================= AVAILABILITY =================

def check_availability(doctor, date):
    """Returns list of booked 24h time strings for that doctor+date."""
    appointments = appointments_sheet.get_all_records()
    booked = []
    for a in appointments:
        if (
            normalize_name(str(a.get("doctor", ""))) == normalize_name(doctor)
            and normalize_date(a.get("date", "")) == normalize_date(date)
            and a.get("status", "") in ["Booked", "Rescheduled"]
        ):
            booked.append(normalize_time(str(a.get("time", ""))))
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
                normalize_name(str(leave.get("doctor", ""))) == normalize_name(doctor)
                and normalize_date(str(leave.get("date", ""))) == normalize_date(date)
            ):
                return True
    except Exception:
        return False
    return False
