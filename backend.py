from fastapi import FastAPI
from pydantic import BaseModel

from database import (
    get_doctors,
    add_doctor,
    delete_doctor,
    get_appointments,
    add_appointment,
    cancel_appointment,
    reschedule_appointment
)

app = FastAPI(title="Hospital API")

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

# ================= ROOT =================

@app.get("/")
def home():

    return {
        "message": "Hospital API Running"
    }

# ================= DOCTORS =================

@app.get("/get_doctors")
def doctors():

    return get_doctors()


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

        delete_doctor(data.name)

        return {
            "message": "Doctor deleted successfully",
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

    return get_appointments()


@app.post("/book_appointment")
def book(data: Appointment):

    print("BOOKING DATA:", data.dict())

    try:

        add_appointment(data.dict())

        return {
            "message": "Appointment booked successfully",
            "success": True
        }

    except Exception as e:

        print("ERROR:", str(e))

        return {
            "message": str(e),
            "success": False
        }


@app.post("/cancel_appointment")
def cancel(data: Cancel):

    try:

        cancel_appointment(
            data.patient_name,
            data.phone
        )

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

        reschedule_appointment(
            data.patient_name,
            data.phone,
            data.new_date,
            data.new_time
        )

        return {
            "message": "Appointment rescheduled",
            "success": True
        }

    except Exception as e:

        return {
            "message": str(e),
            "success": False
        }
