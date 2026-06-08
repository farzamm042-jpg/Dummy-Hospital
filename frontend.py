import streamlit as st
import requests
import pandas as pd

# ================= API =================

API_URL = "https://dummy-hospital-production.up.railway.app"

# ================= PAGE =================

st.set_page_config(
    page_title="Hospital Dashboard",
    page_icon="🏥",
    layout="wide"
)

st.title("🏥 Hospital Dashboard")

# ================= HELPERS =================

def safe_get(url):

    try:
        return requests.get(url).json()

    except:
        return []


def safe_post(url, payload):

    try:

        response = requests.post(
            url,
            json=payload
        )

        return response.json()

    except Exception as e:

        return {
            "message": str(e)
        }

# ================= MENU =================

menu = st.sidebar.radio(
    "Menu",
    [
        "Dashboard",
        "Doctors",
        "Add Doctor",
        "Delete Doctor",
        "Appointments",
        "Book Appointment",
        "Cancel Appointment",
        "Reschedule Appointment"
    ]
)

# ================= DASHBOARD =================

if menu == "Dashboard":

    doctors = safe_get(
        f"{API_URL}/get_doctors"
    )

    appointments = safe_get(
        f"{API_URL}/get_appointments"
    )

    col1, col2 = st.columns(2)

    col1.metric(
        "Doctors",
        len(doctors)
    )

    col2.metric(
        "Appointments",
        len(appointments)
    )

# ================= DOCTORS =================

elif menu == "Doctors":

    doctors = safe_get(
        f"{API_URL}/get_doctors"
    )

    st.dataframe(
        pd.DataFrame(doctors)
    )

# ================= ADD DOCTOR =================

elif menu == "Add Doctor":

    name = st.text_input("Doctor Name")

    specialty = st.text_input("Specialty")

    days = st.text_input("Days")

    start_time = st.text_input("Start Time")

    end_time = st.text_input("End Time")

    fee = st.number_input(
        "Fee",
        min_value=0
    )

    if st.button("Add Doctor"):

        response = safe_post(
            f"{API_URL}/add_doctor",
            {
                "name": name,
                "specialty": specialty,
                "days": days,
                "start_time": start_time,
                "end_time": end_time,
                "fee": int(fee)
            }
        )

        st.success(
            response.get("message")
        )

# ================= DELETE DOCTOR =================

elif menu == "Delete Doctor":

    doctors = safe_get(
        f"{API_URL}/get_doctors"
    )

    doctor_names = [
        d.get("name")
        for d in doctors
    ]

    doctor = st.selectbox(
        "Select Doctor",
        doctor_names
    )

    if st.button("Delete Doctor"):

        response = safe_post(
            f"{API_URL}/delete_doctor",
            {
                "name": doctor
            }
        )

        st.success(
            response.get("message")
        )

# ================= APPOINTMENTS =================

elif menu == "Appointments":

    appointments = safe_get(
        f"{API_URL}/get_appointments"
    )

    st.dataframe(
        pd.DataFrame(appointments)
    )

# ================= BOOK APPOINTMENT =================

elif menu == "Book Appointment":

    doctors = safe_get(
        f"{API_URL}/get_doctors"
    )

    doctor_names = [
        d.get("name")
        for d in doctors
    ]

    patient_name = st.text_input("Patient Name")

    phone = st.text_input("Phone")

    reason = st.text_input("Reason")

    doctor = st.selectbox(
        "Doctor",
        doctor_names
    )

    date = st.date_input("Date")

    time = st.text_input("Time")

    if st.button("Book Appointment"):

        response = safe_post(
            f"{API_URL}/book_appointment",
            {
                "patient_name": patient_name,
                "phone": phone,
                "reason": reason,
                "doctor": doctor,
                "date": str(date),
                "time": time
            }
        )

        st.success(
            response.get("message")
        )

# ================= CANCEL =================

elif menu == "Cancel Appointment":

    patient_name = st.text_input("Patient Name")

    phone = st.text_input("Phone")

    if st.button("Cancel"):

        response = safe_post(
            f"{API_URL}/cancel_appointment",
            {
                "patient_name": patient_name,
                "phone": phone
            }
        )

        st.success(
            response.get("message")
        )

# ================= RESCHEDULE =================

elif menu == "Reschedule Appointment":

    patient_name = st.text_input("Patient Name")

    phone = st.text_input("Phone")

    new_date = st.date_input("New Date")

    new_time = st.text_input("New Time")

    if st.button("Reschedule"):

        response = safe_post(
            f"{API_URL}/reschedule_appointment",
            {
                "patient_name": patient_name,
                "phone": phone,
                "new_date": str(new_date),
                "new_time": new_time
            }
        )

        st.success(
            response.get("message")
        )
