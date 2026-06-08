import streamlit as st
import requests
import pandas as pd

API_URL = "https://dummy-hospital-ai-production.up.railway.app"

st.set_page_config(
    page_title="Dummy Hospital Dashboard",
    page_icon="🏥",
    layout="wide"
)

st.title("🏥 Dummy Hospital Dashboard")

menu = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Book Appointment",
        "Check Availability",
        "Cancel Appointment",
        "Reschedule Appointment",
        "Doctors",
        "Appointments"
    ]
)

# ======================
# DASHBOARD
# ======================

if menu == "Dashboard":

    st.header("Dashboard")

    try:

        appointments = requests.get(
            f"{API_URL}/get_appointments"
        ).json()

        doctors = requests.get(
            f"{API_URL}/get_doctors"
        ).json()

        total_appointments = len(appointments)
        total_doctors = len(doctors)

        booked = len([
            x for x in appointments
            if x["status"] == "Booked"
        ])

        cancelled = len([
            x for x in appointments
            if x["status"] == "Cancelled"
        ])

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Doctors",
            total_doctors
        )

        col2.metric(
            "Appointments",
            total_appointments
        )

        col3.metric(
            "Booked",
            booked
        )

        col4.metric(
            "Cancelled",
            cancelled
        )

    except:
        st.error("Backend not connected")

# ======================
# BOOK APPOINTMENT
# ======================

elif menu == "Book Appointment":

    st.header("Book Appointment")

    doctors = requests.get(
        f"{API_URL}/get_doctors"
    ).json()

    doctor_names = [
        d["name"]
        for d in doctors
    ]

    patient_name = st.text_input(
        "Patient Name"
    )

    phone = st.text_input(
        "Phone Number"
    )

    reason = st.text_input(
        "Reason"
    )

    doctor = st.selectbox(
        "Doctor",
        doctor_names
    )

    date = st.date_input(
        "Appointment Date"
    )

    time = st.selectbox(
        "Time",
        [
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
            "11:30 AM"
        ]
    )

    if st.button("Book"):

        payload = {
            "patient_name": patient_name,
            "phone": phone,
            "reason": reason,
            "doctor": doctor,
            "date": str(date),
            "time": time
        }

        response = requests.post(
            f"{API_URL}/book_appointment",
            json=payload
        )

        st.success(
            response.json()["message"]
        )

# ======================
# CHECK AVAILABILITY
# ======================

elif menu == "Check Availability":

    st.header("Check Availability")

    doctors = requests.get(
        f"{API_URL}/get_doctors"
    ).json()

    doctor_names = [
        d["name"]
        for d in doctors
    ]

    doctor = st.selectbox(
        "Doctor",
        doctor_names
    )

    date = st.date_input(
        "Date"
    )

    if st.button(
        "Check Slots"
    ):

        response = requests.post(
            f"{API_URL}/check_availability",
            json={
                "doctor": doctor,
                "date": str(date)
            }
        )

        st.json(
            response.json()
        )

# ======================
# CANCEL APPOINTMENT
# ======================

elif menu == "Cancel Appointment":

    st.header(
        "Cancel Appointment"
    )

    patient_name = st.text_input(
        "Patient Name"
    )

    phone = st.text_input(
        "Phone Number"
    )

    if st.button(
        "Cancel Appointment"
    ):

        response = requests.post(
            f"{API_URL}/cancel_appointment",
            json={
                "patient_name": patient_name,
                "phone": phone
            }
        )

        st.success(
            response.json()["message"]
        )

# ======================
# RESCHEDULE
# ======================

elif menu == "Reschedule Appointment":

    st.header(
        "Reschedule Appointment"
    )

    patient_name = st.text_input(
        "Patient Name"
    )

    phone = st.text_input(
        "Phone Number"
    )

    new_date = st.date_input(
        "New Date"
    )

    new_time = st.selectbox(
        "New Time",
        [
            "09:00 AM",
            "09:15 AM",
            "09:30 AM",
            "09:45 AM",
            "10:00 AM",
            "10:15 AM",
            "10:30 AM",
            "10:45 AM",
            "11:00 AM"
        ]
    )

    if st.button(
        "Reschedule"
    ):

        response = requests.post(
            f"{API_URL}/reschedule_appointment",
            json={
                "patient_name": patient_name,
                "phone": phone,
                "new_date": str(new_date),
                "new_time": new_time
            }
        )

        st.success(
            response.json()["message"]
        )

# ======================
# DOCTORS
# ======================

elif menu == "Doctors":

    st.header("Doctors")

    tab1, tab2 = st.tabs(
        [
            "View Doctors",
            "Add Doctor"
        ]
    )

    with tab1:

        doctors = requests.get(
            f"{API_URL}/get_doctors"
        ).json()

        st.dataframe(
            pd.DataFrame(doctors),
            use_container_width=True
        )

    with tab2:

        name = st.text_input(
            "Doctor Name"
        )

        specialty = st.text_input(
            "Specialty"
        )

        days = st.text_input(
            "Days"
        )

        start_time = st.text_input(
            "Start Time"
        )

        end_time = st.text_input(
            "End Time"
        )

        fee = st.number_input(
            "Fee",
            min_value=0
        )

        if st.button(
            "Add Doctor"
        ):

            response = requests.post(
                f"{API_URL}/add_doctor",
                json={
                    "name": name,
                    "specialty": specialty,
                    "days": days,
                    "start_time": start_time,
                    "end_time": end_time,
                    "fee": int(fee)
                }
            )

            st.success(
                response.json()["message"]
            )

# ======================
# APPOINTMENTS
# ======================

elif menu == "Appointments":

    st.header(
        "Appointments"
    )

    appointments = requests.get(
        f"{API_URL}/get_appointments"
    ).json()

    df = pd.DataFrame(
        appointments
    )

    st.dataframe(
        df,
        use_container_width=True
    )