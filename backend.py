from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime, date, timedelta

from database import (
    get_doctors,
    add_doctor,
    delete_doctor,
    get_appointments,
    add_appointment,
    cancel_appointment,
    reschedule_appointment,
    check_availability,
    is_slot_available,
    is_doctor_on_leave
)

app = FastAPI(title="Hospital API V4 — Vapi Ready")


# ================= GLOBAL SLOT ENGINE =================

ALLOWED_SLOTS = [
    "09:00 AM", "10:00 AM", "11:00 AM",
    "12:00 PM", "01:00 PM", "02:00 PM",
    "03:00 PM", "04:00 PM", "05:00 PM"
]

# Internal 24-hour versions for comparison
ALLOWED_SLOTS_24 = [
    "09:00", "10:00", "11:00",
    "12:00", "13:00", "14:00",
    "15:00", "16:00", "17:00"
]


# ================= NORMALIZATION ENGINE =================

def normalize_text(text: str) -> str:
    if not text:
        return text
    return " ".join(text.strip().split())


def normalize_phone(phone: str) -> str:
    return str(phone).strip().replace(" ", "").replace("-", "")


def normalize_time_12h(t: str) -> str:
    """
    Converts any time input to HH:MM AM/PM for API responses.
    Handles: 9am, 9AM, 09:00 AM, 09:00, 1pm, 13:00, etc.
    """
    if not t:
        return t

    import re
    t = str(t).strip()
    t_clean = re.sub(r'\s+', '', t).upper()

    # Quick map for short forms
    quick_map = {
        "8AM": "08:00 AM", "9AM": "09:00 AM",
        "10AM": "10:00 AM", "11AM": "11:00 AM",
        "12PM": "12:00 PM", "1PM": "01:00 PM",
        "2PM": "02:00 PM", "3PM": "03:00 PM",
        "4PM": "04:00 PM", "5PM": "05:00 PM",
        "8:00AM": "08:00 AM", "9:00AM": "09:00 AM",
        "10:00AM": "10:00 AM", "11:00AM": "11:00 AM",
        "12:00PM": "12:00 PM", "1:00PM": "01:00 PM",
        "2:00PM": "02:00 PM", "3:00PM": "03:00 PM",
        "4:00PM": "04:00 PM", "5:00PM": "05:00 PM",
    }

    if t_clean in quick_map:
        return quick_map[t_clean]

    # Try parsing HH:MM AM/PM
    for fmt in ["%I:%M %p", "%I:%M%p", "%I %p", "%I%p"]:
        try:
            dt = datetime.strptime(t.upper().strip(), fmt)
            return dt.strftime("%I:%M %p").lstrip("0") if dt.strftime("%I") != "12" else dt.strftime("%I:%M %p")
        except ValueError:
            pass

    # Try 24-hour format and convert
    for fmt in ["%H:%M"]:
        try:
            dt = datetime.strptime(t.strip(), fmt)
            return dt.strftime("%I:%M %p").lstrip("0") or dt.strftime("%I:%M %p")
        except ValueError:
            pass

    return t


def normalize_time_24h(t: str) -> str:
    """
    Converts any time input to HH:MM 24-hour for internal DB comparison.
    """
    if not t:
        return t

    import re
    t = str(t).strip()
    t_clean = re.sub(r'\s+', '', t).upper()

    quick_map_24 = {
        "8AM": "08:00", "9AM": "09:00",
        "10AM": "10:00", "11AM": "11:00",
        "12PM": "12:00", "1PM": "13:00",
        "2PM": "14:00", "3PM": "15:00",
        "4PM": "16:00", "5PM": "17:00",
        "8:00AM": "08:00", "9:00AM": "09:00",
        "10:00AM": "10:00", "11:00AM": "11:00",
        "12:00PM": "12:00", "1:00PM": "13:00",
        "2:00PM": "14:00", "3:00PM": "15:00",
        "4:00PM": "16:00", "5:00PM": "17:00",
    }

    if t_clean in quick_map_24:
        return quick_map_24[t_clean]

    for fmt in ["%I:%M %p", "%I:%M%p", "%I %p", "%I%p"]:
        try:
            dt = datetime.strptime(t.upper().strip(), fmt)
            return dt.strftime("%H:%M")
        except ValueError:
            pass

    if ":" in t and len(t) <= 5:
        try:
            dt = datetime.strptime(t, "%H:%M")
            return dt.strftime("%H:%M")
        except ValueError:
            pass

    return t


def validate_date(date_str: str) -> bool:
    try:
        d = datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
        today = date.today()

        # Must not be in the past
        if d < today:
            return False

        # Must be within current year or next year only
        if d.year < today.year or d.year > today.year + 1:
            return False

        return True

    except Exception:
        return False


# ================= REQUEST SCHEMAS =================

class Doctor(BaseModel):
    name: str
    specialty: str
    days: str
    start_time: str
    end_time: str
    fee: int


class Appointment(BaseModel):
    patient_name: str
    phone: str
    reason: str
    doctor: str
    date: str
    time: str


class Cancel(BaseModel):
    patient_name: str
    phone: str


class Reschedule(BaseModel):
    patient_name: str
    phone: str
    new_date: str
    new_time: str


class Availability(BaseModel):
    doctor: str
    date: str


# ================= BOOKING GUARD =================

def booking_guard(doctor: str, date_str: str, time_str: str):
    """
    Returns "OK" or an error reason string.
    Checks leave first, then slot availability with double-verification.
    """
    if is_doctor_on_leave(doctor, date_str):
        return "DOCTOR_ON_LEAVE"

    time_24 = normalize_time_24h(time_str)

    if not is_slot_available(doctor, date_str, time_24):
        return "SLOT_TAKEN"

    # Double-check directly against DB
    booked = check_availability(doctor, date_str)
    if time_24 in booked:
        return "CONFLICT"

    return "OK"


# ================= DATE TOOL (VAPI FIX) =================

@app.get("/get_current_date")
def get_current_date():
    """
    Returns today, tomorrow, and day-after-tomorrow.
    Vapi agent MUST call this at the start of every conversation
    to get accurate dates — never rely on internal knowledge for dates.
    """
    today = date.today()
    tomorrow = today + timedelta(days=1)
    day_after = today + timedelta(days=2)

    return {
        "today": today.strftime("%Y-%m-%d"),
        "tomorrow": tomorrow.strftime("%Y-%m-%d"),
        "day_after_tomorrow": day_after.strftime("%Y-%m-%d"),
        "today_human": today.strftime("%B %d, %Y"),
        "tomorrow_human": tomorrow.strftime("%B %d, %Y"),
        "day_after_tomorrow_human": day_after.strftime("%B %d, %Y"),
        "current_year": today.year,
        "success": True
    }


# ================= DOCTORS =================

@app.get("/get_doctors")
def doctors():
    return get_doctors()


@app.post("/add_doctor")
def add(data: Doctor):
    add_doctor(data.dict())
    return {"message": "Doctor added successfully", "success": True}


@app.post("/delete_doctor")
def delete(data: Doctor):
    ok = delete_doctor(data.name)
    return {
        "message": "Doctor deleted" if ok else "Doctor not found",
        "success": ok
    }


# ================= AVAILABILITY =================

@app.post("/check_availability")
def availability(data: Availability):
    doctor = normalize_text(data.doctor)
    d = data.date.strip()

    if not validate_date(d):
        return {
            "success": False,
            "message": "Invalid date. Use YYYY-MM-DD format and ensure date is not in the past."
        }

    if is_doctor_on_leave(doctor, d):
        return {
            "doctor": doctor,
            "date": d,
            "available_slots": [],
            "success": False,
            "message": f"{doctor} is on leave on this date. Please choose another date."
        }

    booked_24h = check_availability(doctor, d)

    # Return available slots in 12-hour human format
    available = []
    for slot_12h, slot_24h in zip(ALLOWED_SLOTS, ALLOWED_SLOTS_24):
        if slot_24h not in booked_24h:
            available.append(slot_12h)

    return {
        "doctor": doctor,
        "date": d,
        "available_slots": available,
        "booked_count": len(booked_24h),
        "success": True
    }


# ================= BOOKING ENGINE =================

@app.post("/book_appointment")
def book(data: Appointment):
    doctor = normalize_text(data.doctor)
    name = normalize_text(data.patient_name)
    phone = normalize_phone(data.phone)
    reason = normalize_text(data.reason)
    date_str = data.date.strip()
    time_12h = normalize_time_12h(data.time)
    time_24h = normalize_time_24h(data.time)

    # Validate date
    if not validate_date(date_str):
        return {
            "success": False,
            "message": "Invalid date. Please provide a valid future date in YYYY-MM-DD format."
        }

    # Validate phone (must be 11 digits for Pakistani numbers)
    digits_only = "".join(filter(str.isdigit, phone))
    if len(digits_only) != 11:
        return {
            "success": False,
            "message": f"Phone number must be 11 digits. Got {len(digits_only)} digits."
        }

    # Run booking guard
    result = booking_guard(doctor, date_str, time_24h)

    if result == "DOCTOR_ON_LEAVE":
        return {
            "success": False,
            "message": f"{doctor} is on leave on {date_str}. Please choose another date."
        }

    if result in ["SLOT_TAKEN", "CONFLICT"]:
        return {
            "success": False,
            "message": f"The {time_12h} slot with {doctor} on {date_str} is already booked. Please choose another time."
        }

    # Save with 24h time internally
    add_appointment({
        "patient_name": name,
        "phone": digits_only,
        "reason": reason,
        "doctor": doctor,
        "date": date_str,
        "time": time_24h
    })

    return {
        "success": True,
        "message": f"Appointment booked successfully with {doctor} on {date_str} at {time_12h}.",
        "details": {
            "patient": name,
            "doctor": doctor,
            "date": date_str,
            "time": time_12h,
            "phone": digits_only
        }
    }


# ================= CANCEL =================

@app.post("/cancel_appointment")
def cancel(data: Cancel):
    ok = cancel_appointment(
        normalize_text(data.patient_name),
        normalize_phone(data.phone)
    )

    return {
        "success": ok,
        "message": "Appointment cancelled successfully." if ok else "No active appointment found for this patient and phone number."
    }


# ================= RESCHEDULE =================

@app.post("/reschedule_appointment")
def reschedule(data: Reschedule):
    new_date = data.new_date.strip()

    if not validate_date(new_date):
        return {
            "success": False,
            "message": "Invalid new date. Please provide a valid future date in YYYY-MM-DD format."
        }

    new_time_24h = normalize_time_24h(data.new_time)
    new_time_12h = normalize_time_12h(data.new_time)

    ok = reschedule_appointment(
        normalize_text(data.patient_name),
        normalize_phone(data.phone),
        new_date,
        new_time_24h
    )

    return {
        "success": ok,
        "message": f"Appointment rescheduled to {new_date} at {new_time_12h}." if ok else "No active appointment found for this patient and phone number."
    }


# ================= GET APPOINTMENTS =================

@app.get("/get_appointments")
def appointments():
    return get_appointments()
