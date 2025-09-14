"""
Database migration script for CareCloud Healthcare Database
"""

import asyncio
import logging
from datetime import date, datetime, time
from services.db_service import DBService
from configs.settings import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_tables(db_service: DBService):
    """Create all database tables."""
    try:
        logger.info("Creating database tables...")
        await db_service.create_tables()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create tables: {str(e)}")
        raise

async def insert_sample_data(db_service: DBService):
    """Insert sample healthcare data."""
    try:
        logger.info("Inserting sample data...")

        # Sample patients
        patients_data = [
            {
                "first_name": "John",
                "last_name": "Doe",
                "date_of_birth": date(1985, 3, 15),
                "gender": "Male",
                "phone": "+1234567890",
                "email": "john.doe@email.com",
                "address": "123 Main St, City, State 12345",
                "emergency_contact_name": "Jane Doe",
                "emergency_contact_phone": "+1234567891",
                "insurance_provider": "HealthPlus Insurance",
                "insurance_policy_number": "HP123456789"
            },
            {
                "first_name": "Sarah",
                "last_name": "Johnson",
                "date_of_birth": date(1992, 7, 22),
                "gender": "Female",
                "phone": "+1234567892",
                "email": "sarah.johnson@email.com",
                "address": "456 Oak Ave, City, State 12346",
                "emergency_contact_name": "Mike Johnson",
                "emergency_contact_phone": "+1234567893",
                "insurance_provider": "MediCare Plus",
                "insurance_policy_number": "MC987654321"
            },
            {
                "first_name": "Michael",
                "last_name": "Brown",
                "date_of_birth": date(1978, 11, 8),
                "gender": "Male",
                "phone": "+1234567894",
                "email": "michael.brown@email.com",
                "address": "789 Pine Rd, City, State 12347",
                "emergency_contact_name": "Lisa Brown",
                "emergency_contact_phone": "+1234567895",
                "insurance_provider": "CareFirst Insurance",
                "insurance_policy_number": "CF456789123"
            }
        ]

        # Insert patients
        patient_ids = []
        for patient_data in patients_data:
            patient = await db_service.create_patient(patient_data)
            patient_ids.append(patient.patient_id)
            logger.info(f"Created patient: {patient.first_name} {patient.last_name} (ID: {patient.patient_id})")

        # Sample doctors
        doctors_data = [
            {
                "first_name": "Dr. Emily",
                "last_name": "Davis",
                "specialty": "Cardiology",
                "license_number": "MD123456",
                "phone": "+1555123456",
                "email": "emily.davis@hospital.com",
                "department": "Cardiology",
                "hire_date": date(2015, 6, 1),
                "is_active": True
            },
            {
                "first_name": "Dr. Robert",
                "last_name": "Wilson",
                "specialty": "General Medicine",
                "license_number": "MD789012",
                "phone": "+1555789012",
                "email": "robert.wilson@hospital.com",
                "department": "Internal Medicine",
                "hire_date": date(2018, 3, 15),
                "is_active": True
            },
            {
                "first_name": "Dr. Lisa",
                "last_name": "Garcia",
                "specialty": "Pediatrics",
                "license_number": "MD345678",
                "phone": "+1555345678",
                "email": "lisa.garcia@hospital.com",
                "department": "Pediatrics",
                "hire_date": date(2017, 9, 20),
                "is_active": True
            }
        ]

        # Insert doctors
        doctor_ids = []
        for doctor_data in doctors_data:
            doctor = await db_service.create_doctor(doctor_data)
            doctor_ids.append(doctor.doctor_id)
            logger.info(f"Created doctor: {doctor.first_name} {doctor.last_name} (ID: {doctor.doctor_id})")

        # Sample appointments
        appointments_data = [
            {
                "patient_id": patient_ids[0],
                "doctor_id": doctor_ids[0],
                "appointment_date": date.today(),
                "appointment_time": time(10, 0),
                "duration_minutes": 30,
                "appointment_type": "Consultation",
                "status": "Scheduled",
                "reason_for_visit": "Regular checkup and blood pressure monitoring",
                "notes": "Patient reports occasional dizziness"
            },
            {
                "patient_id": patient_ids[1],
                "doctor_id": doctor_ids[1],
                "appointment_date": date.today(),
                "appointment_time": time(14, 30),
                "duration_minutes": 45,
                "appointment_type": "Follow-up",
                "status": "Scheduled",
                "reason_for_visit": "Follow-up on previous diagnosis",
                "notes": "Review lab results from last visit"
            },
            {
                "patient_id": patient_ids[2],
                "doctor_id": doctor_ids[2],
                "appointment_date": date.today(),
                "appointment_time": time(16, 0),
                "duration_minutes": 30,
                "appointment_type": "Consultation",
                "status": "Scheduled",
                "reason_for_visit": "Annual physical examination",
                "notes": "Complete health assessment required"
            }
        ]

        # Insert appointments
        for appointment_data in appointments_data:
            appointment = await db_service.create_appointment(appointment_data)
            logger.info(f"Created appointment for patient {appointment.patient_id} with doctor {appointment.doctor_id}")

        # Sample diagnoses
        diagnoses_data = [
            {
                "patient_id": patient_ids[0],
                "doctor_id": doctor_ids[0],
                "diagnosis_code": "I10",
                "diagnosis_description": "Essential (primary) hypertension",
                "severity": "Moderate",
                "diagnosis_date": date.today(),
                "notes": "Blood pressure consistently elevated, requires monitoring"
            },
            {
                "patient_id": patient_ids[1],
                "doctor_id": doctor_ids[1],
                "diagnosis_code": "J00",
                "diagnosis_description": "Acute nasopharyngitis (common cold)",
                "severity": "Mild",
                "diagnosis_date": date.today(),
                "notes": "Viral infection, symptoms should resolve within 7-10 days"
            }
        ]

        # Insert diagnoses
        for diagnosis_data in diagnoses_data:
            diagnosis = await db_service.create_diagnosis(diagnosis_data)
            logger.info(f"Created diagnosis for patient {diagnosis.patient_id}: {diagnosis.diagnosis_description}")

        # Sample prescriptions
        prescriptions_data = [
            {
                "patient_id": patient_ids[0],
                "doctor_id": doctor_ids[0],
                "medication_name": "Lisinopril",
                "dosage": "10mg",
                "frequency": "Once daily",
                "duration_days": 90,
                "instructions": "Take with food in the morning",
                "prescription_date": date.today(),
                "status": "Active"
            },
            {
                "patient_id": patient_ids[1],
                "doctor_id": doctor_ids[1],
                "medication_name": "Acetaminophen",
                "dosage": "500mg",
                "frequency": "Every 6 hours as needed",
                "duration_days": 7,
                "instructions": "Take with food, maximum 4 doses per day",
                "prescription_date": date.today(),
                "status": "Active"
            }
        ]

        # Insert prescriptions
        for prescription_data in prescriptions_data:
            prescription = await db_service.create_prescription(prescription_data)
            logger.info(f"Created prescription for patient {prescription.patient_id}: {prescription.medication_name}")

        # Sample vital signs
        vital_signs_data = [
            {
                "patient_id": patient_ids[0],
                "measurement_date": datetime.now(),
                "blood_pressure_systolic": 145,
                "blood_pressure_diastolic": 90,
                "heart_rate": 72,
                "temperature": 98.6,
                "weight_kg": 80.5,
                "height_cm": 175.0,
                "bmi": 26.3,
                "oxygen_saturation": 98,
                "notes": "Blood pressure slightly elevated"
            },
            {
                "patient_id": patient_ids[1],
                "measurement_date": datetime.now(),
                "blood_pressure_systolic": 120,
                "blood_pressure_diastolic": 80,
                "heart_rate": 68,
                "temperature": 99.1,
                "weight_kg": 65.2,
                "height_cm": 165.0,
                "bmi": 24.0,
                "oxygen_saturation": 97,
                "notes": "Mild fever present"
            }
        ]

        # Insert vital signs
        for vital_data in vital_signs_data:
            vital_sign = await db_service.create_vital_sign(vital_data)
            logger.info(f"Created vital signs for patient {vital_sign.patient_id}")

        # Sample lab results
        lab_results_data = [
            {
                "patient_id": patient_ids[0],
                "test_name": "Complete Blood Count",
                "test_category": "Blood",
                "result_value": "Normal",
                "unit": "N/A",
                "reference_range": "Normal ranges",
                "is_abnormal": False,
                "test_date": date.today(),
                "notes": "All values within normal limits"
            },
            {
                "patient_id": patient_ids[1],
                "test_name": "C-Reactive Protein",
                "test_category": "Blood",
                "result_value": "2.1",
                "unit": "mg/L",
                "reference_range": "< 3.0 mg/L",
                "is_abnormal": False,
                "test_date": date.today(),
                "notes": "Slightly elevated, consistent with mild infection"
            }
        ]

        # Insert lab results
        for lab_data in lab_results_data:
            lab_result = await db_service.create_lab_result(lab_data)
            logger.info(f"Created lab result for patient {lab_result.patient_id}: {lab_result.test_name}")

        logger.info("Sample data inserted successfully")

    except Exception as e:
        logger.error(f"Failed to insert sample data: {str(e)}")
        raise

async def main():
    """Main migration function."""
    settings = get_settings()

    db_config = {
        "host": settings.db_host,
        "port": settings.db_port,
        "user": settings.db_user,
        "password": settings.db_password,
        "database": settings.db_name,
    }

    db_service = DBService(db_config)

    try:
        # Initialize database service
        await db_service.initialize()

        # Create tables
        await create_tables(db_service)

        # Insert sample data
        await insert_sample_data(db_service)

        # Get statistics
        stats = await db_service.get_healthcare_stats()
        logger.info("Healthcare Database Statistics:")
        for key, value in stats.items():
            logger.info(f"  {key}: {value}")

    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        raise
    finally:
        await db_service.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
