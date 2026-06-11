import streamlit as st
import requests
import pandas as pd
import json

# ================= CONFIG =================

API_URL = "https://dummy-hospital-production.up.railway.app"

st.set_page_config(
    page_title="Hospital Dashboard",
    page_icon="🏥",
    layout="wide"
)

st.title("🏥 Hospital Dashboard")

# ================= SAFE HELPERS =================

def safe_get(url):
    try:
        res = requests.get(url, timeout=10)
        return res.json()
    except:
        return []

def safe_post(url, payload):
    try:
        res = requests.post(url, json=payload, timeout=10)
        return res.json()
    except Exception as e:
        return {"message": str(e), "success": False}

# ================= SIDEBAR MENU =================

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

    st.subheader("Quick Overview")

    st.write("System Status: 🟢 Running")

# ================= DOCTORS =================

elif menu == "Doctors":

    st.subheader("Doctors List")

    doctors = safe_get(f"{API_URL}/get_doctors")

    if doctors:
        st.dataframe(pd.DataFrame(doctors))
    else:
        st.warning("No doctors found or API not responding.")

# ================= ADD DOCTOR =================

elif menu == "Add Doctor":

    st.subheader("Add New Doctor")

    name = st.text_input("Doctor Name")
    specialty = st.text_input("Specialty")
    days = st.text_input("Days")
    start_time = st.text_input("Start Time (HH:MM)")
    end_time = st.text_input("End Time (HH:MM)")
    fee = st.number_input("Fee", min_value=0)

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

        if response.get("success"):
            st.success(response.get("message"))
        else:
            st.error(response.get("message"))

# ================= DELETE DOCTOR =================

elif menu == "Delete Doctor":

    st.subheader("Delete Doctor")

    doctors = safe_get(f"{API_URL}/get_doctors")

    doctor_names = [d.get("name") for d in doctors]

    doctor = st.selectbox("Select Doctor", doctor_names if doctor_names else ["No doctors"])

    if st.button("Delete Doctor"):

        response = safe_post(
            f"{API_URL}/delete_doctor",
            {"name": doctor}
        )

        if response.get("success"):
            st.success(response.get("message"))
        else:
            st.error(response.get("message"))

# ================= APPOINTMENTS =================

elif menu == "Appointments":

    st.subheader("All Appointments")

    appointments = safe_get(f"{API_URL}/get_appointments")

    if appointments:
        st.dataframe(pd.DataFrame(appointments))
    else:
        st.warning("No appointments found or API error.")

# ================= BOOK APPOINTMENT =================

elif menu == "Book Appointment":

    st.subheader("Book Appointment")

    doctors = safe_get(f"{API_URL}/get_doctors")

    doctor_names = [d.get("name") for d in doctors]

    patient_name = st.text_input("Patient Name")
    phone = st.text_input("Phone")
    reason = st.text_input("Reason")

    doctor = st.selectbox("Doctor", doctor_names if doctor_names else ["No doctors"])

    date = st.date_input("Date")
    time = st.text_input("Time (e.g. 09:00 AM)")

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

        if response.get("success"):
            st.success(response.get("message"))
        else:
            st.error(response.get("message"))

# ================= CANCEL =================

elif menu == "Cancel Appointment":

    st.subheader("Cancel Appointment")

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

        if response.get("success"):
            st.success(response.get("message"))
        else:
            st.error(response.get("message"))

# ================= RESCHEDULE =================

elif menu == "Reschedule Appointment":

    st.subheader("Reschedule Appointment")

    patient_name = st.text_input("Patient Name")
    phone = st.text_input("Phone")
    new_date = st.date_input("New Date")
    new_time = st.text_input("New Time (e.g. 10:00 AM)")

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

        if response.get("success"):
            st.success(response.get("message"))
        else:
            st.error(response.get("message"))
