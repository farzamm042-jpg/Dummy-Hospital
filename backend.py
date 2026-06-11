from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime, date

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

app = FastAPI(title="Hospital API V3 Ultra Stable")


# ================= GLOBAL SLOT ENGINE =================

ALLOWED_SLOTS = [
    "09:00 AM", "10:00 AM", "11:00 AM",
    "12:00 PM", "01:00 PM", "02:00 PM",
    "03:00 PM", "04:00 PM", "05:00 PM"
]


# ================= NORMALIZATION ENGINE =================

def normalize_text(text: str) -> str:
    if not text:
        return text
    return " ".join(text.strip().split())


def normalize_phone(phone: str) -> str:
    return phone.strip().replace(" ", "")


def normalize_time(t: str) -> str:
    if not t:
        return t

    t = t.strip().lower().replace(" ", "")

    mapping = {
        "8am": "08:00 AM",
        "9am": "09:00 AM",
        "10am": "10:00 AM",
        "11am": "11:00 AM",
        "12pm": "12:00 PM",
        "1pm": "01:00 PM",
        "2pm": "02:00 PM",
        "3pm": "03:00 PM",
        "4pm": "04:00 PM",
        "5pm": "05:00 PM",
    }

    return mapping.get(t, t)


def validate_date(date_str: str):
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        today = date.today()

        if d < today:
            return False

        if d.year < today.year or d.year > today.year + 1:
            return False

        return True

    except:
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


# ================= SAFETY ENGINE =================

def safe_doctor(name: str):
    return normalize_text(name)


def safe_date(d: str):
    return d.strip()


def safe_time(t: str):
    return normalize_time(t)


def booking_guard(doctor, date_str, time_str):

    # doctor leave check
    if is_doctor_on_leave(doctor, date_str):
        return "DOCTOR_ON_LEAVE"

    # slot check
    if not is_slot_available(doctor, date_str, time_str):
        return "SLOT_TAKEN"

    # double verify with DB
    if time_str in check_availability(doctor, date_str):
        return "CONFLICT"

    return "OK"


# ================= DOCTORS =================

@app.get("/get_doctors")
def doctors():
    return get_doctors()


@app.post("/add_doctor")
def add(data: Doctor):
    add_doctor(data.dict())
    return {"message": "Doctor added", "success": True}


@app.post("/delete_doctor")
def delete(data: Doctor):
    ok = delete_doctor(data.name)
    return {"message": "Deleted" if ok else "Not found", "success": ok}


# ================= AVAILABILITY =================

@app.post("/check_availability")
def availability(data: Availability):

    doctor = safe_doctor(data.doctor)
    d = safe_date(data.date)

    if not validate_date(d):
        return {"message": "Invalid date", "success": False}

    if is_doctor_on_leave(doctor, d):
        return {
            "doctor": doctor,
            "date": d,
            "available_slots": [],
            "success": False,
            "message": "Doctor on leave"
        }

    booked = check_availability(doctor, d)

    available = [s for s in ALLOWED_SLOTS if s not in booked]

    return {
        "doctor": doctor,
        "date": d,
        "available_slots": available,
        "success": True
    }


# ================= BOOKING ENGINE (V3 CORE) =================

@app.post("/book_appointment")
def book(data: Appointment):

    doctor = safe_doctor(data.doctor)
    name = normalize_text(data.patient_name)
    phone = normalize_phone(data.phone)
    reason = normalize_text(data.reason)
    date_str = safe_date(data.date)
    time_str = safe_time(data.time)

    # validate date
    if not validate_date(date_str):
        return {"message": "Invalid date", "success": False}

    # guard engine
    result = booking_guard(doctor, date_str, time_str)

    if result == "DOCTOR_ON_LEAVE":
        return {"message": "Doctor is on leave", "success": False}

    if result == "SLOT_TAKEN":
        return {"message": "Slot already booked", "success": False}

    if result == "CONFLICT":
        return {"message": "Slot conflict detected", "success": False}

    # final insert
    add_appointment({
        "patient_name": name,
        "phone": phone,
        "reason": reason,
        "doctor": doctor,
        "date": date_str,
        "time": time_str
    })

    return {
        "message": "Appointment booked successfully",
        "success": True
    }


# ================= CANCEL =================

@app.post("/cancel_appointment")
def cancel(data: Cancel):

    ok = cancel_appointment(
        normalize_text(data.patient_name),
        normalize_phone(data.phone)
    )

    return {
        "message": "Cancelled" if ok else "Not found",
        "success": ok
    }


# ================= RESCHEDULE =================

@app.post("/reschedule_appointment")
def reschedule(data: Reschedule):

    if not validate_date(data.new_date):
        return {"message": "Invalid date", "success": False}

    ok = reschedule_appointment(
        normalize_text(data.patient_name),
        normalize_phone(data.phone),
        data.new_date,
        normalize_time(data.new_time)
    )

    return {
        "message": "Rescheduled" if ok else "Not found",
        "success": ok
    }
