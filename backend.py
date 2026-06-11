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

app = FastAPI(title="Hospital API")


# ================= UTILITIES =================

def normalize_text(text: str) -> str:
    if not text:
        return text
    return " ".join(text.strip().split())


def normalize_time(time_str: str) -> str:
    if not time_str:
        return time_str

    t = time_str.strip().lower().replace(" ", "")

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

    return mapping.get(t, time_str.strip())


def validate_date(date_str: str):
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        today = date.today()

        # must not be past
        if d < today:
            return False

        # must be current or next year only
        if d.year < today.year or d.year > today.year + 1:
            return False

        return True

    except:
        return False


# ================= SCHEMAS =================

class Doctor(BaseModel):
    name: str
    specialty: str
    days: str
    start_time: str
    end_time: str
    fee: int


class DeleteDoctor(BaseModel):
    name: str


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


# ================= DOCTORS =================

@app.get("/get_doctors")
def doctors():
    return get_doctors()


@app.post("/add_doctor")
def add(data: Doctor):
    add_doctor(data.dict())
    return {"message": "Doctor added successfully", "success": True}


@app.post("/delete_doctor")
def delete(data: DeleteDoctor):
    deleted = delete_doctor(data.name)

    if not deleted:
        return {"message": "Doctor not found", "success": False}

    return {"message": "Doctor deleted successfully", "success": True}


# ================= AVAILABILITY =================

@app.post("/check_availability")
def availability(data: Availability):

    doctor = normalize_text(data.doctor)
    d = data.date.strip()

    if not validate_date(d):
        return {"message": "Invalid date", "success": False}

    if is_doctor_on_leave(doctor, d):
        return {
            "doctor": doctor,
            "date": d,
            "available_slots": [],
            "message": "Doctor on leave",
            "success": False
        }

    booked = check_availability(doctor, d)

    slots = [
        "09:00 AM", "10:00 AM", "11:00 AM",
        "12:00 PM", "01:00 PM", "02:00 PM",
        "03:00 PM", "04:00 PM", "05:00 PM"
    ]

    available = [s for s in slots if s not in booked]

    return {
        "doctor": doctor,
        "date": d,
        "available_slots": available,
        "success": True
    }


# ================= APPOINTMENTS =================

@app.get("/get_appointments")
def appointments():
    return get_appointments()


# ================= BOOK =================

@app.post("/book_appointment")
def book(data: Appointment):

    doctor = normalize_text(data.doctor)
    name = normalize_text(data.patient_name)
    phone = data.phone.strip()
    reason = data.reason.strip()
    d = data.date.strip()
    t = normalize_time(data.time)

    if not validate_date(d):
        return {"message": "Invalid date", "success": False}

    if is_doctor_on_leave(doctor, d):
        return {"message": "Doctor is on leave", "success": False}

    if not is_slot_available(doctor, d, t):
        return {"message": "Slot already booked", "success": False}

    if t in check_availability(doctor, d):
        return {"message": "Conflict detected", "success": False}

    add_appointment({
        "patient_name": name,
        "phone": phone,
        "reason": reason,
        "doctor": doctor,
        "date": d,
        "time": t
    })

    return {"message": "Appointment booked successfully", "success": True}


# ================= CANCEL =================

@app.post("/cancel_appointment")
def cancel(data: Cancel):

    ok = cancel_appointment(data.patient_name, data.phone)

    if not ok:
        return {"message": "Not found", "success": False}

    return {"message": "Cancelled", "success": True}


# ================= RESCHEDULE =================

@app.post("/reschedule_appointment")
def reschedule(data: Reschedule):

    if not validate_date(data.new_date):
        return {"message": "Invalid date", "success": False}

    ok = reschedule_appointment(
        data.patient_name,
        data.phone,
        data.new_date,
        data.new_time
    )

    if not ok:
        return {"message": "Not found", "success": False}

    return {"message": "Rescheduled successfully", "success": True}
