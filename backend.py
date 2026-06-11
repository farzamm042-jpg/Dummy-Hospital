from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime

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

# ================= HELPERS =================

def validate_date(date_str):

    try:

        date_obj = datetime.strptime(
            date_str,
            "%Y-%m-%d"
        )

        current_year = datetime.now().year

        if date_obj.year != current_year:
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

# ================= ROOT =================

@app.get("/")
def home():

    return {
        "message": "Hospital API Running",
        "success": True
    }

# ================= DOCTORS =================

@app.get("/get_doctors")
def doctors():

    try:

        return get_doctors()

    except Exception as e:

        return {
            "message": str(e),
            "success": False
        }


@app.post("/add_doctor")
def add(data: Doctor):

    try:

        add_doctor(data.dict())

        return {
            "message": "Doctor added successfully",
            "success": True
        }

    except Exception as e:

        return {
            "message": str(e),
            "success": False
        }


@app.post("/delete_doctor")
def delete(data: DeleteDoctor):

    try:

        deleted = delete_doctor(data.name)

        if not deleted:

            return {
                "message": "Doctor not found",
                "success": False
            }

        return {
            "message": "Doctor deleted successfully",
            "success": True
        }

    except Exception as e:

        return {
            "message": str(e),
            "success": False
        }

# ================= AVAILABILITY =================

@app.post("/check_availability")
def availability(data: Availability):

    try:

        if not validate_date(data.date):

            return {
                "message": f"Invalid date. Use current year ({datetime.now().year}) and YYYY-MM-DD format.",
                "success": False
            }

        if is_doctor_on_leave(
            data.doctor,
            data.date
        ):

            return {
                "doctor": data.doctor,
                "date": data.date,
                "available_slots": [],
                "message": "Doctor is on leave",
                "success": False
            }

        booked = check_availability(
            data.doctor,
            data.date
        )

        all_slots = [
            "09:00 AM",
            "10:00 AM",
            "11:00 AM",
            "12:00 PM",
            "01:00 PM",
            "02:00 PM",
            "03:00 PM",
            "04:00 PM",
            "05:00 PM"
        ]

        available = []

        for slot in all_slots:

            if slot not in booked:
                available.append(slot)

        return {
            "doctor": data.doctor,
            "date": data.date,
            "available_slots": available,
            "success": True
        }

    except Exception as e:

        return {
            "message": str(e),
            "success": False
        }

# ================= APPOINTMENTS =================

@app.get("/get_appointments")
def appointments():

    try:

        return get_appointments()

    except Exception as e:

        return {
            "message": str(e),
            "success": False
        }


@app.post("/book_appointment")
def book(data: Appointment):

    try:

        if not validate_date(data.date):

            return {
                "message": f"Invalid date. Use current year ({datetime.now().year}) and YYYY-MM-DD format.",
                "success": False
            }

        if is_doctor_on_leave(
            data.doctor,
            data.date
        ):

            return {
                "message": "Doctor is on leave",
                "success": False
            }

        if not is_slot_available(
            data.doctor,
            data.date,
            data.time
        ):

            return {
                "message": "Slot already booked",
                "success": False
            }

        add_appointment(
            data.dict()
        )

        return {
            "message": "Appointment booked successfully",
            "success": True
        }

    except Exception as e:

        return {
            "message": str(e),
            "success": False
        }


@app.post("/cancel_appointment")
def cancel(data: Cancel):

    try:

        cancelled = cancel_appointment(
            data.patient_name,
            data.phone
        )

        if not cancelled:

            return {
                "message": "Appointment not found",
                "success": False
            }

        return {
            "message": "Appointment cancelled",
            "success": True
        }

    except Exception as e:

        return {
            "message": str(e),
            "success": False
        }


@app.post("/reschedule_appointment")
def reschedule(data: Reschedule):

    try:

        if not validate_date(data.new_date):

            return {
                "message": f"Invalid date. Use current year ({datetime.now().year}) and YYYY-MM-DD format.",
                "success": False
            }

        updated = reschedule_appointment(
            data.patient_name,
            data.phone,
            data.new_date,
            data.new_time
        )

        if not updated:

            return {
                "message": "Appointment not found",
                "success": False
            }

        return {
            "message": "Appointment rescheduled",
            "success": True
        }

    except Exception as e:

        return {
            "message": str(e),
            "success": False
        }
