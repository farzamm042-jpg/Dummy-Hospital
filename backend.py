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
    is_doctor_on_leave,
    get_doctor_row_by_name,
    is_doctor_working_on_date,
    get_day_name,
    normalize_time,
)

app = FastAPI(title="Hospital API V5 — Day-Check Ready")


# ================= GLOBAL SLOT ENGINE =================

ALLOWED_SLOTS = [
    "09:00 AM", "10:00 AM", "11:00 AM",
    "12:00 PM", "01:00 PM", "02:00 PM",
    "03:00 PM", "04:00 PM", "05:00 PM"
]

ALLOWED_SLOTS_24 = [
    "09:00", "10:00", "11:00",
    "12:00", "13:00", "14:00",
    "15:00", "16:00", "17:00"
]


# ================= NORMALIZATION =================

def normalize_text(text: str) -> str:
    if not text:
        return text
    return " ".join(text.strip().split())


def normalize_phone(phone: str) -> str:
    return str(phone).strip().replace(" ", "").replace("-", "")


def normalize_time_12h(t: str) -> str:
    """Converts any time input to HH:MM AM/PM for API responses."""
    if not t:
        return t

    import re
    t = str(t).strip()
    t_clean = re.sub(r'\s+', '', t).upper()

    quick_map = {
        "8AM": "08:00 AM",  "9AM": "09:00 AM",
        "10AM": "10:00 AM", "11AM": "11:00 AM",
        "12PM": "12:00 PM", "1PM":  "01:00 PM",
        "2PM":  "02:00 PM", "3PM":  "03:00 PM",
        "4PM":  "04:00 PM", "5PM":  "05:00 PM",
        "8:00AM": "08:00 AM",  "9:00AM": "09:00 AM",
        "10:00AM": "10:00 AM", "11:00AM": "11:00 AM",
        "12:00PM": "12:00 PM", "1:00PM":  "01:00 PM",
        "2:00PM":  "02:00 PM", "3:00PM":  "03:00 PM",
        "4:00PM":  "04:00 PM", "5:00PM":  "05:00 PM",
    }
    if t_clean in quick_map:
        return quick_map[t_clean]

    for fmt in ["%I:%M %p", "%I:%M%p", "%I %p", "%I%p"]:
        try:
            dt = datetime.strptime(t.upper().strip(), fmt)
            return dt.strftime("%I:%M %p")
        except ValueError:
            pass

    try:
        dt = datetime.strptime(t.strip(), "%H:%M")
        return dt.strftime("%I:%M %p")
    except ValueError:
        pass

    return t


def normalize_time_24h(t: str) -> str:
    """Converts any time input to HH:MM 24-hour for DB comparison."""
    if not t:
        return t

    import re
    t = str(t).strip()
    t_clean = re.sub(r'\s+', '', t).upper()

    quick_map_24 = {
        "8AM": "08:00",  "9AM": "09:00",
        "10AM": "10:00", "11AM": "11:00",
        "12PM": "12:00", "1PM":  "13:00",
        "2PM":  "14:00", "3PM":  "15:00",
        "4PM":  "16:00", "5PM":  "17:00",
        "8:00AM": "08:00",  "9:00AM": "09:00",
        "10:00AM": "10:00", "11:00AM": "11:00",
        "12:00PM": "12:00", "1:00PM":  "13:00",
        "2:00PM":  "14:00", "3:00PM":  "15:00",
        "4:00PM":  "16:00", "5:00PM":  "17:00",
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
        if d < today:
            return False
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
    Order: leave check → slot check → double-verify
    """
    if is_doctor_on_leave(doctor, date_str):
        return "DOCTOR_ON_LEAVE"

    time_24 = normalize_time_24h(time_str)

    if not is_slot_available(doctor, date_str, time_24):
        return "SLOT_TAKEN"

    booked = check_availability(doctor, date_str)
    if time_24 in booked:
        return "CONFLICT"

    return "OK"


# ================= DATE TOOL =================

@app.get("/get_current_date")
def get_current_date():
    """
    Vapi agent calls this at the very start of every conversation.
    Provides accurate today/tomorrow dates — AI must never guess dates.
    """
    today     = date.today()
    tomorrow  = today + timedelta(days=1)
    day_after = today + timedelta(days=2)

    return {
        "success": True,
        "today":                    today.strftime("%Y-%m-%d"),
        "tomorrow":                 tomorrow.strftime("%Y-%m-%d"),
        "day_after_tomorrow":       day_after.strftime("%Y-%m-%d"),
        "today_human":              today.strftime("%B %d, %Y"),
        "tomorrow_human":           tomorrow.strftime("%B %d, %Y"),
        "day_after_tomorrow_human": day_after.strftime("%B %d, %Y"),
        "current_year":             today.year,
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


# ================= AVAILABILITY (WITH DAY CHECK) =================

@app.post("/check_availability")
def availability(data: Availability):
    doctor  = normalize_text(data.doctor)
    d       = data.date.strip()
    day_name = get_day_name(d)

    # 1. Date format + range validation
    if not validate_date(d):
        return {
            "success": False,
            "message": "Invalid date. Use YYYY-MM-DD format and ensure date is not in the past."
        }

    # 2. *** DAY-OF-WEEK CHECK *** — THE BIG FIX
    doctor_row = get_doctor_row_by_name(doctor)
    if doctor_row and not is_doctor_working_on_date(doctor_row, d):
        working_days = doctor_row.get("days", "")
        return {
            "success": False,
            "available": False,
            "day_check_failed": True,
            "message": (
                f"{doctor} does not work on {day_name}s. "
                f"Working days are: {working_days}. "
                f"Please ask the patient to choose a different date."
            )
        }

    # 3. Leave check
    if is_doctor_on_leave(doctor, d):
        return {
            "success": False,
            "available": False,
            "doctor": doctor,
            "date": d,
            "day": day_name,
            "available_slots": [],
            "message": f"{doctor} is on leave on {d}. Please choose another date."
        }

    # 4. Build available slots dynamically from doctor's hours
    available_slots = []
    if doctor_row:
        try:
            start_h = int(doctor_row.get("start_time", "09:00").split(":")[0])
            end_h   = int(doctor_row.get("end_time",   "17:00").split(":")[0])
        except Exception:
            start_h, end_h = 9, 17

        booked_24h = check_availability(doctor, d)

        for h in range(start_h, end_h):
            slot_24 = f"{h:02d}:00"
            if slot_24 not in booked_24h:
                # Convert to 12h for human-readable response
                slot_12 = normalize_time_12h(slot_24)
                available_slots.append(slot_12)
    else:
        # Fallback: use global allowed slots
        booked_24h = check_availability(doctor, d)
        for slot_12, slot_24 in zip(ALLOWED_SLOTS, ALLOWED_SLOTS_24):
            if slot_24 not in booked_24h:
                available_slots.append(slot_12)

    if not available_slots:
        return {
            "success": True,
            "available": False,
            "doctor": doctor,
            "date": d,
            "day": day_name,
            "available_slots": [],
            "message": f"No available slots for {doctor} on {d} ({day_name}). All slots are booked."
        }

    return {
        "success": True,
        "available": True,
        "doctor": doctor,
        "date": d,
        "day": day_name,
        "available_slots": available_slots,
        "message": f"Available slots for {doctor} on {d} ({day_name}): {', '.join(available_slots)}"
    }


# ================= BOOKING ENGINE =================

@app.post("/book_appointment")
def book(data: Appointment):
    doctor   = normalize_text(data.doctor)
    name     = normalize_text(data.patient_name)
    phone    = normalize_phone(data.phone)
    reason   = normalize_text(data.reason)
    date_str = data.date.strip()
    day_name = get_day_name(date_str)
    time_12h = normalize_time_12h(data.time)
    time_24h = normalize_time_24h(data.time)

    # 1. Date validation
    if not validate_date(date_str):
        return {
            "success": False,
            "message": "Invalid date. Please provide a valid future date in YYYY-MM-DD format."
        }

    # 2. Phone validation
    digits_only = "".join(filter(str.isdigit, phone))
    if len(digits_only) != 11:
        return {
            "success": False,
            "message": f"Phone number must be 11 digits. Got {len(digits_only)} digits."
        }

    # 3. Day-of-week check (double protection)
    doctor_row = get_doctor_row_by_name(doctor)
    if doctor_row and not is_doctor_working_on_date(doctor_row, date_str):
        working_days = doctor_row.get("days", "")
        return {
            "success": False,
            "message": (
                f"{doctor} does not work on {day_name}s. "
                f"Working days: {working_days}. "
                f"Please choose a different date."
            )
        }

    # 4. Booking guard (leave + slot conflict)
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

    # 5. Save appointment
    add_appointment({
        "patient_name": name,
        "phone":        digits_only,
        "reason":       reason,
        "doctor":       doctor,
        "date":         date_str,
        "time":         time_24h,
    })

    return {
        "success": True,
        "message": f"Appointment booked successfully with {doctor} on {date_str} at {time_12h}.",
        "details": {
            "patient": name,
            "doctor":  doctor,
            "date":    date_str,
            "time":    time_12h,
            "phone":   digits_only,
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
        "message": "Appointment cancelled successfully." if ok
                   else "No active appointment found for this patient and phone number."
    }


# ================= RESCHEDULE =================

@app.post("/reschedule_appointment")
def reschedule(data: Reschedule):
    new_date    = data.new_date.strip()
    day_name    = get_day_name(new_date)
    new_time_24 = normalize_time_24h(data.new_time)
    new_time_12 = normalize_time_12h(data.new_time)

    # Date validation
    if not validate_date(new_date):
        return {
            "success": False,
            "message": "Invalid new date. Please provide a valid future date in YYYY-MM-DD format."
        }

    ok = reschedule_appointment(
        normalize_text(data.patient_name),
        normalize_phone(data.phone),
        new_date,
        new_time_24,
    )

    return {
        "success": ok,
        "message": f"Appointment rescheduled to {new_date} ({day_name}) at {new_time_12}." if ok
                   else "No active appointment found for this patient and phone number."
    }


# ================= GET APPOINTMENTS =================

@app.get("/get_appointments")
def appointments():
    return get_appointments()
