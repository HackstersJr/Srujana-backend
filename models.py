"""
SQLAlchemy models for CareCloud Healthcare Database
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Text, Date, DateTime, Time, Boolean,
    Float, Numeric, ForeignKey, CheckConstraint, Index, func
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Patient(Base):
    """Patient information and demographics"""
    __tablename__ = "patients"

    patient_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    date_of_birth: Mapped[Date] = mapped_column(Date, nullable=False)
    gender: Mapped[str] = mapped_column(String(10), CheckConstraint("gender IN ('Male', 'Female', 'Other')"))
    phone: Mapped[Optional[str]] = mapped_column(String(15))
    email: Mapped[Optional[str]] = mapped_column(String(100))
    address: Mapped[Optional[str]] = mapped_column(Text)
    emergency_contact_name: Mapped[Optional[str]] = mapped_column(String(100))
    emergency_contact_phone: Mapped[Optional[str]] = mapped_column(String(15))
    insurance_provider: Mapped[Optional[str]] = mapped_column(String(100))
    insurance_policy_number: Mapped[Optional[str]] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    appointments: Mapped[List["Appointment"]] = relationship("Appointment", back_populates="patient")
    diagnoses: Mapped[List["Diagnosis"]] = relationship("Diagnosis", back_populates="patient")
    prescriptions: Mapped[List["Prescription"]] = relationship("Prescription", back_populates="patient")
    vital_signs: Mapped[List["VitalSign"]] = relationship("VitalSign", back_populates="patient")
    lab_results: Mapped[List["LabResult"]] = relationship("LabResult", back_populates="patient")
    medical_history: Mapped[List["MedicalHistory"]] = relationship("MedicalHistory", back_populates="patient")
    medication_history: Mapped[List["MedicationHistory"]] = relationship("MedicationHistory", back_populates="patient")

    def __repr__(self):
        return f"<Patient(patient_id={self.patient_id}, name='{self.first_name} {self.last_name}')>"


class Doctor(Base):
    """Healthcare provider information"""
    __tablename__ = "doctors"

    doctor_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    specialty: Mapped[Optional[str]] = mapped_column(String(100))
    license_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(15))
    email: Mapped[Optional[str]] = mapped_column(String(100))
    department: Mapped[Optional[str]] = mapped_column(String(100))
    hire_date: Mapped[Optional[Date]] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    appointments: Mapped[List["Appointment"]] = relationship("Appointment", back_populates="doctor")
    diagnoses: Mapped[List["Diagnosis"]] = relationship("Diagnosis", back_populates="doctor")
    prescriptions: Mapped[List["Prescription"]] = relationship("Prescription", back_populates="doctor")
    medication_history: Mapped[List["MedicationHistory"]] = relationship("MedicationHistory", back_populates="prescribed_by_doctor")

    def __repr__(self):
        return f"<Doctor(doctor_id={self.doctor_id}, name='Dr. {self.first_name} {self.last_name}', specialty='{self.specialty}')>"


class Appointment(Base):
    """Medical appointments"""
    __tablename__ = "appointments"

    appointment_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.patient_id"), nullable=False)
    doctor_id: Mapped[int] = mapped_column(Integer, ForeignKey("doctors.doctor_id"), nullable=False)
    appointment_date: Mapped[Date] = mapped_column(Date, nullable=False)
    appointment_time: Mapped[Time] = mapped_column(Time, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30)
    appointment_type: Mapped[Optional[str]] = mapped_column(String(50))  # 'Consultation', 'Follow-up', 'Emergency'
    status: Mapped[str] = mapped_column(String(20), default='Scheduled')
    __table_args__ = (
        CheckConstraint("status IN ('Scheduled', 'Completed', 'Cancelled', 'No-show')", name="check_appointment_status"),
    )
    reason_for_visit: Mapped[Optional[str]] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="appointments")
    doctor: Mapped["Doctor"] = relationship("Doctor", back_populates="appointments")
    diagnoses: Mapped[List["Diagnosis"]] = relationship("Diagnosis", back_populates="appointment")
    prescriptions: Mapped[List["Prescription"]] = relationship("Prescription", back_populates="appointment")
    vital_signs: Mapped[List["VitalSign"]] = relationship("VitalSign", back_populates="appointment")
    lab_results: Mapped[List["LabResult"]] = relationship("LabResult", back_populates="appointment")

    def __repr__(self):
        return f"<Appointment(appointment_id={self.appointment_id}, patient_id={self.patient_id}, doctor_id={self.doctor_id}, date={self.appointment_date})>"


class Diagnosis(Base):
    """Medical diagnoses"""
    __tablename__ = "diagnoses"

    diagnosis_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.patient_id"), nullable=False)
    doctor_id: Mapped[int] = mapped_column(Integer, ForeignKey("doctors.doctor_id"), nullable=False)
    appointment_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("appointments.appointment_id"))
    diagnosis_code: Mapped[Optional[str]] = mapped_column(String(20))  # ICD-10 codes
    diagnosis_description: Mapped[Optional[str]] = mapped_column(Text)
    severity: Mapped[Optional[str]] = mapped_column(String(20),
                                                   CheckConstraint("severity IN ('Mild', 'Moderate', 'Severe', 'Critical')"))
    diagnosis_date: Mapped[Date] = mapped_column(Date, default=func.current_date())
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="diagnoses")
    doctor: Mapped["Doctor"] = relationship("Doctor", back_populates="diagnoses")
    appointment: Mapped[Optional["Appointment"]] = relationship("Appointment", back_populates="diagnoses")

    def __repr__(self):
        return f"<Diagnosis(diagnosis_id={self.diagnosis_id}, patient_id={self.patient_id}, code='{self.diagnosis_code}')>"


class Prescription(Base):
    """Medication prescriptions"""
    __tablename__ = "prescriptions"

    prescription_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.patient_id"), nullable=False)
    doctor_id: Mapped[int] = mapped_column(Integer, ForeignKey("doctors.doctor_id"), nullable=False)
    appointment_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("appointments.appointment_id"))
    medication_name: Mapped[str] = mapped_column(String(100), nullable=False)
    dosage: Mapped[Optional[str]] = mapped_column(String(50))
    frequency: Mapped[Optional[str]] = mapped_column(String(50))
    duration_days: Mapped[Optional[int]] = mapped_column(Integer)
    instructions: Mapped[Optional[str]] = mapped_column(Text)
    prescription_date: Mapped[Date] = mapped_column(Date, default=func.current_date())
    status: Mapped[str] = mapped_column(String(20), default='Active')
    __table_args__ = (
        CheckConstraint("status IN ('Active', 'Completed', 'Discontinued')", name="check_prescription_status"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="prescriptions")
    doctor: Mapped["Doctor"] = relationship("Doctor", back_populates="prescriptions")
    appointment: Mapped[Optional["Appointment"]] = relationship("Appointment", back_populates="prescriptions")

    def __repr__(self):
        return f"<Prescription(prescription_id={self.prescription_id}, patient_id={self.patient_id}, medication='{self.medication_name}')>"


class VitalSign(Base):
    """Vital signs and medical measurements"""
    __tablename__ = "vital_signs"

    vital_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.patient_id"), nullable=False)
    appointment_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("appointments.appointment_id"))
    measurement_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    blood_pressure_systolic: Mapped[Optional[int]] = mapped_column(Integer)
    blood_pressure_diastolic: Mapped[Optional[int]] = mapped_column(Integer)
    heart_rate: Mapped[Optional[int]] = mapped_column(Integer)
    temperature: Mapped[Optional[float]] = mapped_column(Numeric(precision=4, scale=1))
    weight_kg: Mapped[Optional[float]] = mapped_column(Numeric(precision=5, scale=2))
    height_cm: Mapped[Optional[float]] = mapped_column(Numeric(precision=5, scale=2))
    bmi: Mapped[Optional[float]] = mapped_column(Numeric(precision=4, scale=1))
    oxygen_saturation: Mapped[Optional[int]] = mapped_column(Integer)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="vital_signs")
    appointment: Mapped[Optional["Appointment"]] = relationship("Appointment", back_populates="vital_signs")

    def __repr__(self):
        return f"<VitalSign(vital_id={self.vital_id}, patient_id={self.patient_id}, date={self.measurement_date})>"


class LabResult(Base):
    """Laboratory test results"""
    __tablename__ = "lab_results"

    lab_result_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.patient_id"), nullable=False)
    appointment_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("appointments.appointment_id"))
    test_name: Mapped[Optional[str]] = mapped_column(String(100))
    test_category: Mapped[Optional[str]] = mapped_column(String(50))  # 'Blood', 'Urine', 'Imaging', etc.
    result_value: Mapped[Optional[str]] = mapped_column(String(50))
    unit: Mapped[Optional[str]] = mapped_column(String(20))
    reference_range: Mapped[Optional[str]] = mapped_column(String(50))
    is_abnormal: Mapped[Optional[bool]] = mapped_column(Boolean)
    test_date: Mapped[Optional[Date]] = mapped_column(Date)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="lab_results")
    appointment: Mapped[Optional["Appointment"]] = relationship("Appointment", back_populates="lab_results")

    def __repr__(self):
        return f"<LabResult(lab_result_id={self.lab_result_id}, patient_id={self.patient_id}, test='{self.test_name}')>"


class MedicalHistory(Base):
    """Patient medical history"""
    __tablename__ = "medical_history"

    history_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.patient_id"), nullable=False)
    condition_name: Mapped[Optional[str]] = mapped_column(String(100))
    diagnosis_date: Mapped[Optional[Date]] = mapped_column(Date)
    status: Mapped[Optional[str]] = mapped_column(String(20),
                                                 CheckConstraint("status IN ('Active', 'Resolved', 'Chronic')"))
    severity: Mapped[Optional[str]] = mapped_column(String(20))
    treatment: Mapped[Optional[str]] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="medical_history")

    def __repr__(self):
        return f"<MedicalHistory(history_id={self.history_id}, patient_id={self.patient_id}, condition='{self.condition_name}')>"


class MedicationHistory(Base):
    """Patient medication history"""
    __tablename__ = "medication_history"

    med_history_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.patient_id"), nullable=False)
    medication_name: Mapped[Optional[str]] = mapped_column(String(100))
    dosage: Mapped[Optional[str]] = mapped_column(String(50))
    start_date: Mapped[Optional[Date]] = mapped_column(Date)
    end_date: Mapped[Optional[Date]] = mapped_column(Date)
    reason: Mapped[Optional[str]] = mapped_column(Text)
    prescribed_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("doctors.doctor_id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="medication_history")
    prescribed_by_doctor: Mapped[Optional["Doctor"]] = relationship("Doctor", back_populates="medication_history")

    def __repr__(self):
        return f"<MedicationHistory(med_history_id={self.med_history_id}, patient_id={self.patient_id}, medication='{self.medication_name}')>"


# Create indexes for better performance
Index('idx_patients_name', Patient.last_name, Patient.first_name)
Index('idx_patients_dob', Patient.date_of_birth)
Index('idx_patients_phone', Patient.phone)

Index('idx_appointments_patient_date', Appointment.patient_id, Appointment.appointment_date)
Index('idx_appointments_doctor_date', Appointment.doctor_id, Appointment.appointment_date)
Index('idx_appointments_date_status', Appointment.appointment_date, Appointment.status)

Index('idx_diagnoses_patient', Diagnosis.patient_id)
Index('idx_diagnoses_code', Diagnosis.diagnosis_code)

Index('idx_prescriptions_patient', Prescription.patient_id)
Index('idx_prescriptions_medication', Prescription.medication_name)

Index('idx_vital_signs_patient_date', VitalSign.patient_id, VitalSign.measurement_date)

Index('idx_lab_results_patient', LabResult.patient_id)
Index('idx_lab_results_test', LabResult.test_name, LabResult.test_date)
