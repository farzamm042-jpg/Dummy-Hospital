from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import (
    get_db,
    Doctor,
    Appointment
)

app = FastAPI(
    title="Hospital AI Backend"
)

# ===================================
# SCHEMAS
# ===================================

class AvailabilityRequest(BaseModel):
    doctor: str
    date: str


class BookAppointmentRequest(BaseModel):
    patient_name: str
    phone: str
    reason: str
    doctor: str
    date: str
    time: str


class CancelAppointmentRequest(BaseModel):
    patient_name: str
    phone: str


class RescheduleAppointmentRequest(BaseModel):
    patient_name: str
    phone: str
    new_date: str
    new_time: str


class AddDoctorRequest(BaseModel):
    name: str
    specialty: str
    days: str
    start_time: str
    end_time: str
    fee: int


# ===================================
# HOME
# ===================================

@app.get("/")
def home():
    return {
        "message": "Hospital AI Backend Running"
    }


# ===================================
# HOSPITAL INFO
# ===================================

@app.get("/get_hospital_info")
def get_hospital_info():

    return {
        "hospital_name": "City Care Hospital",
        "timings": "24/7",
        "emergency": True,
        "address": "Dubai Healthcare City",
        "contact": "+971500000000"
    }


# ===================================
# DOCTORS
# ===================================

@app.get("/get_doctors")
def get_doctors(
    db: Session = Depends(get_db)
):

    doctors = db.query(
        Doctor
    ).all()

    return [
        {
            "id": d.id,
            "name": d.name,
            "specialty": d.specialty,
            "days": d.days,
            "start_time": d.start_time,
            "end_time": d.end_time,
            "fee": d.fee
        }
        for d in doctors
    ]


@app.post("/add_doctor")
def add_doctor(
    data: AddDoctorRequest,
    db: Session = Depends(get_db)
):

    doctor = Doctor(
        name=data.name,
        specialty=data.specialty,
        days=data.days,
        start_time=data.start_time,
        end_time=data.end_time,
        fee=data.fee
    )

    db.add(doctor)
    db.commit()

    return {
        "success": True,
        "message": "Doctor added successfully"
    }


@app.delete("/delete_doctor/{doctor_id}")
def delete_doctor(
    doctor_id: int,
    db: Session = Depends(get_db)
):

    doctor = db.query(
        Doctor
    ).filter(
        Doctor.id == doctor_id
    ).first()

    if not doctor:
        return {
            "success": False,
            "message": "Doctor not found"
        }

    db.delete(doctor)
    db.commit()

    return {
        "success": True,
        "message": "Doctor deleted successfully"
    }


# ===================================
# CHECK AVAILABILITY
# ===================================

@app.post("/check_availability")
def check_availability(
    data: AvailabilityRequest,
    db: Session = Depends(get_db)
):

    booked = db.query(
        Appointment
    ).filter(
        Appointment.doctor == data.doctor,
        Appointment.date == data.date,
        Appointment.status == "Booked"
    ).all()

    booked_slots = [
        x.time for x in booked
    ]

    all_slots = [
        "09:00 AM",
        "09:15 AM",
        "09:30 AM",
        "09:45 AM",
        "10:00 AM",
        "10:15 AM",
        "10:30 AM",
        "10:45 AM",
        "11:00 AM",
        "11:15 AM",
        "11:30 AM",
        "11:45 AM",
        "12:00 PM",
        "12:15 PM",
        "12:30 PM",
        "12:45 PM"
    ]

    available = [
        slot
        for slot in all_slots
        if slot not in booked_slots
    ]

    return {
        "doctor": data.doctor,
        "date": data.date,
        "available_slots": available
    }


# ===================================
# BOOK APPOINTMENT
# ===================================

@app.post("/book_appointment")
def book_appointment(
    data: BookAppointmentRequest,
    db: Session = Depends(get_db)
):

    existing = db.query(
        Appointment
    ).filter(
        Appointment.doctor == data.doctor,
        Appointment.date == data.date,
        Appointment.time == data.time,
        Appointment.status == "Booked"
    ).first()

    if existing:
        return {
            "success": False,
            "message": "Slot already booked"
        }

    appointment = Appointment(
        patient_name=data.patient_name,
        phone=data.phone,
        reason=data.reason,
        doctor=data.doctor,
        date=data.date,
        time=data.time
    )

    db.add(appointment)
    db.commit()
    db.refresh(appointment)

    return {
        "success": True,
        "appointment_id": appointment.id,
        "message": "Appointment booked successfully"
    }


# ===================================
# GET APPOINTMENTS
# ===================================

@app.get("/get_appointments")
def get_appointments(
    db: Session = Depends(get_db)
):

    appointments = db.query(
        Appointment
    ).all()

    return [
        {
            "id": a.id,
            "patient_name": a.patient_name,
            "phone": a.phone,
            "reason": a.reason,
            "doctor": a.doctor,
            "date": a.date,
            "time": a.time,
            "status": a.status
        }
        for a in appointments
    ]


# ===================================
# CANCEL APPOINTMENT
# ===================================

@app.post("/cancel_appointment")
def cancel_appointment(
    data: CancelAppointmentRequest,
    db: Session = Depends(get_db)
):

    appointment = db.query(
        Appointment
    ).filter(
        Appointment.patient_name == data.patient_name,
        Appointment.phone == data.phone
    ).first()

    if not appointment:

        return {
            "success": False,
            "message": "Appointment not found"
        }

    appointment.status = "Cancelled"

    db.commit()

    return {
        "success": True,
        "message": "Appointment cancelled successfully"
    }


# ===================================
# RESCHEDULE
# ===================================

@app.post("/reschedule_appointment")
def reschedule_appointment(
    data: RescheduleAppointmentRequest,
    db: Session = Depends(get_db)
):

    appointment = db.query(
        Appointment
    ).filter(
        Appointment.patient_name == data.patient_name,
        Appointment.phone == data.phone
    ).first()

    if not appointment:

        return {
            "success": False,
            "message": "Appointment not found"
        }

    slot_exists = db.query(
        Appointment
    ).filter(
        Appointment.doctor == appointment.doctor,
        Appointment.date == data.new_date,
        Appointment.time == data.new_time,
        Appointment.status == "Booked"
    ).first()

    if slot_exists:

        return {
            "success": False,
            "message": "Requested slot already booked"
        }

    appointment.date = data.new_date
    appointment.time = data.new_time
    appointment.status = "Rescheduled"

    db.commit()

    return {
        "success": True,
        "message": "Appointment rescheduled successfully"
    }


# ===================================
# DELETE APPOINTMENT
# ===================================

@app.delete("/delete_appointment/{appointment_id}")
def delete_appointment(
    appointment_id: int,
    db: Session = Depends(get_db)
):

    appointment = db.query(
        Appointment
    ).filter(
        Appointment.id == appointment_id
    ).first()

    if not appointment:

        return {
            "success": False,
            "message": "Appointment not found"
        }

    db.delete(appointment)
    db.commit()

    return {
        "success": True,
        "message": "Appointment deleted successfully"
    }