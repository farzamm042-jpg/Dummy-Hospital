from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime
)

from sqlalchemy.orm import (
    declarative_base,
    sessionmaker
)

from datetime import datetime

# =========================
# DATABASE CONFIG
# =========================

DATABASE_URL = "sqlite:///./hospital.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

# =========================
# DOCTORS TABLE
# =========================

class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    name = Column(
        String,
        nullable=False
    )

    specialty = Column(
        String,
        nullable=False
    )

    days = Column(
        String,
        nullable=False
    )

    start_time = Column(
        String,
        nullable=False
    )

    end_time = Column(
        String,
        nullable=False
    )

    fee = Column(
        Integer,
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

# =========================
# APPOINTMENTS TABLE
# =========================

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    patient_name = Column(
        String,
        nullable=False
    )

    phone = Column(
        String,
        nullable=False
    )

    reason = Column(
        String,
        nullable=False
    )

    doctor = Column(
        String,
        nullable=False
    )

    date = Column(
        String,
        nullable=False
    )

    time = Column(
        String,
        nullable=False
    )

    status = Column(
        String,
        default="Booked"
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

# =========================
# DATABASE SESSION
# =========================

def get_db():
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()

# =========================
# CREATE TABLES
# =========================

Base.metadata.create_all(
    bind=engine
)

# =========================
# DEFAULT DOCTORS
# =========================

def seed_doctors():

    db = SessionLocal()

    try:

        existing = db.query(
            Doctor
        ).count()

        if existing == 0:

            doctors = [

                Doctor(
                    name="Dr Sara Ali",
                    specialty="Cardiologist",
                    days="Monday-Friday",
                    start_time="09:00 AM",
                    end_time="03:00 PM",
                    fee=500
                ),

                Doctor(
                    name="Dr Ahmed Khan",
                    specialty="General Physician",
                    days="Monday-Saturday",
                    start_time="10:00 AM",
                    end_time="05:00 PM",
                    fee=300
                ),

                Doctor(
                    name="Dr Bilal Farooq",
                    specialty="Dermatologist",
                    days="Monday-Friday",
                    start_time="11:00 AM",
                    end_time="06:00 PM",
                    fee=700
                )

            ]

            db.add_all(
                doctors
            )

            db.commit()

            print(
                "Default doctors inserted successfully."
            )

    finally:
        db.close()

# =========================
# AUTO INSERT DOCTORS
# =========================

seed_doctors()