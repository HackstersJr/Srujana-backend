"""
PostgreSQL Database Service for managing database operations.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union

import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import QueuePool

# Import healthcare models
from models import (
    Base, Patient, Doctor, Appointment, Diagnosis, Prescription,
    VitalSign, LabResult, MedicalHistory, MedicationHistory
)


class DBService:
    """
    PostgreSQL Database Service for handling database operations.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the database service.

        Args:
            config: Database configuration
        """
        self.config = config or {}
        self.engine = None
        self.async_engine = None
        self.session_factory = None
        self.async_session_factory = None
        self.logger = logging.getLogger(__name__)

    async def initialize(self) -> None:
        """Initialize database connections."""
        try:
            self.logger.info("Initializing database service")

            # Build connection strings
            sync_url = self._build_sync_url()
            async_url = self._build_async_url()

            # Create engines
            self.engine = create_engine(
                sync_url,
                poolclass=QueuePool,
                pool_size=self.config.get("pool_size", 10),
                max_overflow=self.config.get("max_overflow", 20),
                pool_pre_ping=True,
                echo=self.config.get("echo", False),
            )

            self.async_engine = create_async_engine(
                async_url,
                pool_size=self.config.get("pool_size", 10),
                max_overflow=self.config.get("max_overflow", 20),
                pool_pre_ping=True,
                echo=self.config.get("echo", False),
            )

            # Create session factories
            self.session_factory = sessionmaker(bind=self.engine)
            self.async_session_factory = sessionmaker(
                bind=self.async_engine, class_=AsyncSession, expire_on_commit=False
            )

            # Test connections
            await self._test_connections()

            self.logger.info("Database service initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize database service: {str(e)}")
            raise

    def _build_sync_url(self) -> str:
        """Build synchronous database URL."""
        host = self.config.get("host", "localhost")
        port = self.config.get("port", 5432)
        user = self.config.get("user", "postgres")
        password = self.config.get("password", "")
        database = self.config.get("database", "carecloud")

        return f"postgresql://{user}:{password}@{host}:{port}/{database}"

    def _build_async_url(self) -> str:
        """Build asynchronous database URL."""
        host = self.config.get("host", "localhost")
        port = self.config.get("port", 5432)
        user = self.config.get("user", "postgres")
        password = self.config.get("password", "")
        database = self.config.get("database", "carecloud")

        return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"

    async def _test_connections(self) -> None:
        """Test database connections."""
        try:
            # Test sync connection
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()

            # Test async connection
            async with self.async_engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                result.fetchone()

            self.logger.info("Database connections tested successfully")

        except Exception as e:
            self.logger.error(f"Database connection test failed: {str(e)}")
            raise

    async def execute_query(
        self, query: str, params: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query asynchronously.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            List of result dictionaries
        """
        try:
            async with self.async_engine.connect() as conn:
                result = await conn.execute(text(query), params or {})
                rows = result.fetchall()

                # Convert to list of dictionaries
                columns = result.keys()
                return [dict(zip(columns, row)) for row in rows]

        except Exception as e:
            self.logger.error(f"Failed to execute query: {str(e)}")
            raise

    async def execute_non_query(self, query: str, params: Optional[Dict] = None) -> int:
        """
        Execute an INSERT/UPDATE/DELETE query asynchronously.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Number of affected rows
        """
        try:
            async with self.async_engine.connect() as conn:
                async with conn.begin():
                    result = await conn.execute(text(query), params or {})
                    return result.rowcount

        except Exception as e:
            self.logger.error(f"Failed to execute non-query: {str(e)}")
            raise

    async def bulk_insert(self, table_name: str, data: List[Dict[str, Any]]) -> int:
        """
        Perform bulk insert operation.

        Args:
            table_name: Name of the table
            data: List of dictionaries to insert

        Returns:
            Number of inserted rows
        """
        try:
            if not data:
                return 0

            # Build INSERT query
            columns = list(data[0].keys())
            placeholders = ", ".join([f":{col}" for col in columns])
            query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"

            async with self.async_engine.connect() as conn:
                async with conn.begin():
                    result = await conn.execute(text(query), data)
                    return result.rowcount

        except Exception as e:
            self.logger.error(f"Failed to bulk insert: {str(e)}")
            raise

    def execute_query_sync(
        self, query: str, params: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query synchronously.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            List of result dictionaries
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query), params or {})
                rows = result.fetchall()

                # Convert to list of dictionaries
                columns = result.keys()
                return [dict(zip(columns, row)) for row in rows]

        except Exception as e:
            self.logger.error(f"Failed to execute sync query: {str(e)}")
            raise

    def execute_non_query_sync(self, query: str, params: Optional[Dict] = None) -> int:
        """
        Execute an INSERT/UPDATE/DELETE query synchronously.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Number of affected rows
        """
        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    result = conn.execute(text(query), params or {})
                    return result.rowcount

        except Exception as e:
            self.logger.error(f"Failed to execute sync non-query: {str(e)}")
            raise

    async def create_tables(self) -> None:
        """Create database tables from models."""
        try:
            async with self.async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            self.logger.info("Database tables created successfully")

        except Exception as e:
            self.logger.error(f"Failed to create tables: {str(e)}")
            raise

    async def drop_tables(self) -> None:
        """Drop all database tables."""
        try:
            async with self.async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)

            self.logger.info("Database tables dropped successfully")

        except Exception as e:
            self.logger.error(f"Failed to drop tables: {str(e)}")
            raise

    async def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """
        Get information about a database table.

        Args:
            table_name: Name of the table

        Returns:
            Table information
        """
        try:
            query = """
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = :table_name
                ORDER BY ordinal_position
            """

            columns = await self.execute_query(query, {"table_name": table_name})

            return {
                "table_name": table_name,
                "columns": columns,
                "column_count": len(columns),
            }

        except Exception as e:
            self.logger.error(f"Failed to get table info: {str(e)}")
            raise

    async def backup_table(self, table_name: str, backup_file: str) -> None:
        """
        Backup a table to a file.

        Args:
            table_name: Name of the table to backup
            backup_file: Path to backup file
        """
        try:
            query = f"SELECT * FROM {table_name}"
            data = await self.execute_query(query)

            import json

            with open(backup_file, "w") as f:
                json.dump(data, f, indent=2, default=str)

            self.logger.info(f"Table {table_name} backed up to {backup_file}")

        except Exception as e:
            self.logger.error(f"Failed to backup table: {str(e)}")
            raise

    async def cleanup(self) -> None:
        """Cleanup database connections."""
        try:
            self.logger.info("Cleaning up database service")

            if self.async_engine:
                await self.async_engine.dispose()

            if self.engine:
                self.engine.dispose()

            self.logger.info("Database service cleanup completed")

        except Exception as e:
            self.logger.error(f"Failed to cleanup database service: {str(e)}")
            raise

    # ORM Methods for Healthcare Database

    async def create_patient(self, patient_data: Dict[str, Any]) -> Patient:
        """Create a new patient record."""
        try:
            async with self.async_session_factory() as session:
                patient = Patient(**patient_data)
                session.add(patient)
                await session.commit()
                await session.refresh(patient)
                return patient
        except Exception as e:
            self.logger.error(f"Failed to create patient: {str(e)}")
            raise

    async def get_patient(self, patient_id: int) -> Optional[Patient]:
        """Get patient by ID."""
        try:
            async with self.async_session_factory() as session:
                return await session.get(Patient, patient_id)
        except Exception as e:
            self.logger.error(f"Failed to get patient: {str(e)}")
            raise

    async def get_patients(self, limit: int = 100, offset: int = 0) -> List[Patient]:
        """Get list of patients with pagination."""
        try:
            async with self.async_session_factory() as session:
                result = await session.execute(
                    text("SELECT * FROM patients ORDER BY patient_id LIMIT :limit OFFSET :offset"),
                    {"limit": limit, "offset": offset}
                )
                return result.fetchall()
        except Exception as e:
            self.logger.error(f"Failed to get patients: {str(e)}")
            raise

    async def create_doctor(self, doctor_data: Dict[str, Any]) -> Doctor:
        """Create a new doctor record."""
        try:
            async with self.async_session_factory() as session:
                doctor = Doctor(**doctor_data)
                session.add(doctor)
                await session.commit()
                await session.refresh(doctor)
                return doctor
        except Exception as e:
            self.logger.error(f"Failed to create doctor: {str(e)}")
            raise

    async def get_doctor(self, doctor_id: int) -> Optional[Doctor]:
        """Get doctor by ID."""
        try:
            async with self.async_session_factory() as session:
                return await session.get(Doctor, doctor_id)
        except Exception as e:
            self.logger.error(f"Failed to get doctor: {str(e)}")
            raise

    async def create_appointment(self, appointment_data: Dict[str, Any]) -> Appointment:
        """Create a new appointment."""
        try:
            async with self.async_session_factory() as session:
                appointment = Appointment(**appointment_data)
                session.add(appointment)
                await session.commit()
                await session.refresh(appointment)
                return appointment
        except Exception as e:
            self.logger.error(f"Failed to create appointment: {str(e)}")
            raise

    async def get_patient_appointments(self, patient_id: int) -> List[Appointment]:
        """Get appointments for a patient."""
        try:
            async with self.async_session_factory() as session:
                result = await session.execute(
                    text("""
                        SELECT a.*, d.first_name as doctor_first_name, d.last_name as doctor_last_name
                        FROM appointments a
                        JOIN doctors d ON a.doctor_id = d.doctor_id
                        WHERE a.patient_id = :patient_id
                        ORDER BY a.appointment_date DESC, a.appointment_time DESC
                    """),
                    {"patient_id": patient_id}
                )
                return result.fetchall()
        except Exception as e:
            self.logger.error(f"Failed to get patient appointments: {str(e)}")
            raise

    async def create_diagnosis(self, diagnosis_data: Dict[str, Any]) -> Diagnosis:
        """Create a new diagnosis record."""
        try:
            async with self.async_session_factory() as session:
                diagnosis = Diagnosis(**diagnosis_data)
                session.add(diagnosis)
                await session.commit()
                await session.refresh(diagnosis)
                return diagnosis
        except Exception as e:
            self.logger.error(f"Failed to create diagnosis: {str(e)}")
            raise

    async def get_patient_diagnoses(self, patient_id: int) -> List[Diagnosis]:
        """Get diagnoses for a patient."""
        try:
            async with self.async_session_factory() as session:
                result = await session.execute(
                    text("""
                        SELECT d.*, doc.first_name as doctor_first_name, doc.last_name as doctor_last_name
                        FROM diagnoses d
                        JOIN doctors doc ON d.doctor_id = doc.doctor_id
                        WHERE d.patient_id = :patient_id
                        ORDER BY d.diagnosis_date DESC
                    """),
                    {"patient_id": patient_id}
                )
                return result.fetchall()
        except Exception as e:
            self.logger.error(f"Failed to get patient diagnoses: {str(e)}")
            raise

    async def create_prescription(self, prescription_data: Dict[str, Any]) -> Prescription:
        """Create a new prescription."""
        try:
            async with self.async_session_factory() as session:
                prescription = Prescription(**prescription_data)
                session.add(prescription)
                await session.commit()
                await session.refresh(prescription)
                return prescription
        except Exception as e:
            self.logger.error(f"Failed to create prescription: {str(e)}")
            raise

    async def get_patient_prescriptions(self, patient_id: int) -> List[Prescription]:
        """Get prescriptions for a patient."""
        try:
            async with self.async_session_factory() as session:
                result = await session.execute(
                    text("""
                        SELECT p.*, d.first_name as doctor_first_name, d.last_name as doctor_last_name
                        FROM prescriptions p
                        JOIN doctors d ON p.doctor_id = d.doctor_id
                        WHERE p.patient_id = :patient_id
                        ORDER BY p.prescription_date DESC
                    """),
                    {"patient_id": patient_id}
                )
                return result.fetchall()
        except Exception as e:
            self.logger.error(f"Failed to get patient prescriptions: {str(e)}")
            raise

    async def create_vital_sign(self, vital_data: Dict[str, Any]) -> VitalSign:
        """Create a new vital sign record."""
        try:
            async with self.async_session_factory() as session:
                vital_sign = VitalSign(**vital_data)
                session.add(vital_sign)
                await session.commit()
                await session.refresh(vital_sign)
                return vital_sign
        except Exception as e:
            self.logger.error(f"Failed to create vital sign: {str(e)}")
            raise

    async def get_patient_vitals(self, patient_id: int, limit: int = 50) -> List[VitalSign]:
        """Get vital signs for a patient."""
        try:
            async with self.async_session_factory() as session:
                result = await session.execute(
                    text("""
                        SELECT * FROM vital_signs
                        WHERE patient_id = :patient_id
                        ORDER BY measurement_date DESC
                        LIMIT :limit
                    """),
                    {"patient_id": patient_id, "limit": limit}
                )
                return result.fetchall()
        except Exception as e:
            self.logger.error(f"Failed to get patient vitals: {str(e)}")
            raise

    async def create_lab_result(self, lab_data: Dict[str, Any]) -> LabResult:
        """Create a new lab result."""
        try:
            async with self.async_session_factory() as session:
                lab_result = LabResult(**lab_data)
                session.add(lab_result)
                await session.commit()
                await session.refresh(lab_result)
                return lab_result
        except Exception as e:
            self.logger.error(f"Failed to create lab result: {str(e)}")
            raise

    async def get_patient_lab_results(self, patient_id: int) -> List[LabResult]:
        """Get lab results for a patient."""
        try:
            async with self.async_session_factory() as session:
                result = await session.execute(
                    text("""
                        SELECT * FROM lab_results
                        WHERE patient_id = :patient_id
                        ORDER BY test_date DESC
                    """),
                    {"patient_id": patient_id}
                )
                return result.fetchall()
        except Exception as e:
            self.logger.error(f"Failed to get patient lab results: {str(e)}")
            raise

    async def get_healthcare_stats(self) -> Dict[str, Any]:
        """Get healthcare database statistics."""
        try:
            async with self.async_engine.connect() as conn:
                # Patient statistics
                patient_count = await conn.execute(text("SELECT COUNT(*) FROM patients"))
                patient_count = patient_count.fetchone()[0]

                # Doctor statistics
                doctor_count = await conn.execute(text("SELECT COUNT(*) FROM doctors"))
                doctor_count = doctor_count.fetchone()[0]

                # Appointment statistics
                appointment_count = await conn.execute(text("SELECT COUNT(*) FROM appointments"))
                appointment_count = appointment_count.fetchone()[0]

                # Today's appointments
                today_appointments = await conn.execute(
                    text("SELECT COUNT(*) FROM appointments WHERE appointment_date = CURRENT_DATE")
                )
                today_appointments = today_appointments.fetchone()[0]

                # Active prescriptions
                active_prescriptions = await conn.execute(
                    text("SELECT COUNT(*) FROM prescriptions WHERE status = 'Active'")
                )
                active_prescriptions = active_prescriptions.fetchone()[0]

                return {
                    "total_patients": patient_count,
                    "total_doctors": doctor_count,
                    "total_appointments": appointment_count,
                    "today_appointments": today_appointments,
                    "active_prescriptions": active_prescriptions,
                }

        except Exception as e:
            self.logger.error(f"Failed to get healthcare stats: {str(e)}")
            raise
