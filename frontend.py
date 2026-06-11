import streamlit as st
import requests
import pandas as pd

# ================= API =================

API_URL = "https://dummy-hospital-production.up.railway.app"

# ================= PAGE CONFIG =================

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
        response = requests.post(url, json=payload)
        return response.json()
    except Exception as e:
        return {"message": str(e)}

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

    doctors = safe_get(f"{API_URL}/get_doctors")
    appointments = safe_get(f"{API_URL}/get_appointments")

    col1, col2 = st.columns(2)

    col1.metric("Doctors", len(doctors))
    col2.metric("Appointments", len(appointments))

# ================= DOCTORS =================

elif menu == "Doctors":

    doctors = safe_get(f"{API_URL}/get_doctors")

    st.subheader("Doctors List")
    st.dataframe(pd.DataFrame(doctors))

# ================= ADD DOCTOR =================

elif menu == "Add Doctor":

    st.subheader("Add New Doctor")

    name = st.text_input("Doctor Name")
    specialty = st.text_input("Specialty")
    days = st.text_input("Days")
    start_time = st.text_input("Start Time")
    end_time = st.text_input("End Time")

    fee = st.number_input("Fee", min_value=0)

    if st.button("Add Doctor"):

        if not name:
            st.error("Doctor name is required")
        else:
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

            st.success(response.get("message"))

# ================= DELETE DOCTOR =================

elif menu == "Delete Doctor":

    st.subheader("Delete Doctor")

    doctors = safe_get(f"{API_URL}/get_doctors")

    doctor_names = [d.get("name") for d in doctors if d.get("name")]

    if doctor_names:

        doctor = st.selectbox("Select Doctor", doctor_names)

        if st.button("Delete Doctor"):

            response = safe_post(
                f"{API_URL}/delete_doctor",
                {"name": doctor}
            )

            st.success(response.get("message"))

    else:
        st.warning("No doctors available")

# ================= APPOINTMENTS =================

elif menu == "Appointments":

    st.subheader("All Appointments")

    appointments = safe_get(f"{API_URL}/get_appointments")

    st.dataframe(pd.DataFrame(appointments))

# ================= BOOK APPOINTMENT =================

elif menu == "Book Appointment":

    st.subheader("Book New Appointment")

    doctors = safe_get(f"{API_URL}/get_doctors")
    doctor_names = [d.get("name") for d in doctors if d.get("name")]

    patient_name = st.text_input("Patient Name")
    phone = st.text_input("Phone")
    reason = st.text_input("Reason")

    if doctor_names:
        doctor = st.selectbox("Doctor", doctor_names)
    else:
        st.warning("No doctors available")
        doctor = None

    date = st.date_input("Date")

    # ✅ FIXED TIME INPUT (NO MORE TEXT BUGS)
    time = st.selectbox(
        "Time",
        [
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
    )

    if st.button("Book Appointment"):

        if not patient_name or not phone or not doctor:
            st.error("Please fill all required fields")
        else:
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

            st.success(response.get("message"))

# ================= CANCEL =================

elif menu == "Cancel Appointment":

    st.subheader("Cancel Appointment")

    patient_name = st.text_input("Patient Name")
    phone = st.text_input("Phone")

    if st.button("Cancel"):

        if not patient_name or not phone:
            st.error("Please enter all details")
        else:
            response = safe_post(
                f"{API_URL}/cancel_appointment",
                {
                    "patient_name": patient_name,
                    "phone": phone
                }
            )

            st.success(response.get("message"))

# ================= RESCHEDULE =================

elif menu == "Reschedule Appointment":

    st.subheader("Reschedule Appointment")

    patient_name = st.text_input("Patient Name")
    phone = st.text_input("Phone")

    new_date = st.date_input("New Date")

    new_time = st.selectbox(
        "New Time",
        [
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
    )

    if st.button("Reschedule"):

        if not patient_name or not phone:
            st.error("Please enter all details")
        else:
            response = safe_post(
                f"{API_URL}/reschedule_appointment",
                {
                    "patient_name": patient_name,
                    "phone": phone,
                    "new_date": str(new_date),
                    "new_time": new_time
                }
            )

            st.success(response.get("message"))
