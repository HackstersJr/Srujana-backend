"""
Prisma Database Service for managing database operations using raw SQL.
Fallback implementation that doesn't require Prisma client generation.
"""

import logging
import os
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timezone

# Use direct database connections
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    import asyncpg
except ImportError:
    # Fallback for when packages aren't available
    psycopg2 = None
    asyncpg = None


class PrismaService:
    """
    Database Service for handling healthcare database operations using raw SQL.

    This is a lightweight fallback implementation that uses asyncpg/psycopg2
    directly when the Prisma client cannot be generated in containerized
    or restricted environments.
    """

    def __init__(self):
        """
        Initialize the database service.
        """
        self.logger = logging.getLogger(__name__)
        self._connected = False
        self._sync_conn = None
        self._async_conn = None

        # Database configuration
        self.db_config = {
            "host": os.getenv("DB_HOST", "localhost"),
            "user": os.getenv("DB_USER", "postgres"),
            "password": os.getenv("DB_PASSWORD", "postgres123"),
            "database": os.getenv("DB_NAME", "carecloud")
        }

    async def connect(self) -> None:
        """Connect to the database."""
        try:
            if not self._connected:
                if asyncpg:
                    # Create async connection
                    self._async_conn = await asyncpg.connect(**self.db_config)

                if psycopg2:
                    # Create sync connection
                    self._sync_conn = psycopg2.connect(**self.db_config)

                self._connected = True
                self.logger.info("Database connection established")
        except Exception as e:
            self.logger.error(f"Failed to connect to database: {str(e)}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from the database."""
        try:
            if self._connected:
                if self._async_conn and asyncpg:
                    await self._async_conn.close()
                if self._sync_conn and psycopg2:
                    self._sync_conn.close()
                self._connected = False
                self.logger.info("Database connection closed")
        except Exception as e:
            self.logger.error(f"Failed to disconnect from database: {str(e)}")
            raise

    # Generic query execution for complex queries
    async def execute_raw_query(self, query: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a raw SQL query and return results as dictionaries.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            List of result dictionaries
        """
        try:
            if not self._connected:
                await self.connect()

            if asyncpg:
                # Use a short-lived asyncpg connection per call to avoid event-loop issues
                conn = None
                try:
                    conn = await asyncpg.connect(**self.db_config)
                    rows = await conn.fetch(query, *(params or []))
                    return [dict(row) for row in rows]
                finally:
                    if conn:
                        await conn.close()
            else:
                # Fallback to sync connection
                if psycopg2:
                    with self._sync_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                        cursor.execute(query, params or [])
                        rows = cursor.fetchall()
                        return [dict(row) for row in rows]
                else:
                    raise Exception("No database connection available")

        except Exception as e:
            self.logger.error(f"Failed to execute raw query: {str(e)}")
            raise

    async def execute_raw_command(self, query: str, params: Optional[List[Any]] = None) -> int:
        """
        Execute a raw SQL command (INSERT, UPDATE, DELETE).

        Args:
            query: SQL command string
            params: Command parameters

        Returns:
            Number of affected rows
        """
        try:
            if not self._connected:
                await self.connect()

            if self._async_conn and asyncpg:
                # Use a short-lived asyncpg connection per command
                conn = None
                try:
                    conn = await asyncpg.connect(**self.db_config)
                    result = await conn.execute(query, *(params or []))
                    return int(result.split()[-1]) if result else 0
                finally:
                    if conn:
                        await conn.close()
            else:
                # Fallback to sync connection
                if psycopg2:
                    with self._sync_conn.cursor() as cursor:
                        cursor.execute(query, params or [])
                        self._sync_conn.commit()
                        return cursor.rowcount
                else:
                    raise Exception("No database connection available")

        except Exception as e:
            self.logger.error(f"Failed to execute raw command: {str(e)}")
            raise

    # Simplified CRUD operations using raw SQL

    async def create_patient(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new patient."""
        try:
            query = """
                INSERT INTO patients (
                    id, "firstName", "lastName", "dateOfBirth", gender, phone, email, address,
                    "emergencyContact", "medicalHistory", allergies, "bloodType", "createdAt", "updatedAt"
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW(), NOW())
                RETURNING *
            """
            # Ensure dateOfBirth is a datetime/datetime.date for asyncpg
            dob = data.get("dateOfBirth")
            if isinstance(dob, str):
                try:
                    # Accept ISO8601-like strings
                    dob = datetime.fromisoformat(dob.replace("Z", "+00:00"))
                except Exception:
                    # Fallback: let the DB reject if still invalid
                    dob = None

            # If we have a datetime (either provided or parsed), normalize to naive UTC
            if isinstance(dob, datetime) and dob.tzinfo is not None:
                try:
                    # Convert to UTC then drop tzinfo
                    dob = dob.astimezone(tz=timezone.utc).replace(tzinfo=None)
                except Exception:
                    # Fallback: leave as-is and let asyncpg handle or raise
                    pass

            # Generate patient id (UUID) to match Prisma schema expectations
            import uuid
            patient_id = str(uuid.uuid4())

            params = [
                patient_id,
                data.get("firstName"),
                data.get("lastName"),
                dob,
                data.get("gender"),
                data.get("phone"),
                data.get("email"),
                data.get("address"),
                data.get("emergencyContact"),
                data.get("medicalHistory"),
                data.get("allergies"),
                data.get("bloodType")
            ]

            result = await self.execute_raw_query(query, params)
            if result:
                self.logger.info(f"Created patient: {result[0]['id']}")
                return result[0]
            else:
                raise Exception("Failed to create patient")

        except Exception as e:
            self.logger.error(f"Failed to create patient: {str(e)}")
            raise

    async def upsert_patient(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert or update a patient based on unique email (upsert)."""
        try:
            import uuid
            patient_id = str(uuid.uuid4())

            query = """
                INSERT INTO patients (
                    id, "firstName", "lastName", "dateOfBirth", gender, phone, email, address,
                    "emergencyContact", "medicalHistory", allergies, "bloodType", "createdAt", "updatedAt"
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW(), NOW())
                ON CONFLICT (email) DO UPDATE SET
                    "firstName" = EXCLUDED."firstName",
                    "lastName" = EXCLUDED."lastName",
                    "dateOfBirth" = EXCLUDED."dateOfBirth",
                    gender = EXCLUDED.gender,
                    phone = EXCLUDED.phone,
                    address = EXCLUDED.address,
                    "emergencyContact" = EXCLUDED."emergencyContact",
                    "medicalHistory" = EXCLUDED."medicalHistory",
                    allergies = EXCLUDED.allergies,
                    "bloodType" = EXCLUDED."bloodType",
                    "updatedAt" = NOW()
                RETURNING *
            """

            # Normalize dateOfBirth similarly to create_patient
            dob = data.get("dateOfBirth")
            if isinstance(dob, str):
                try:
                    dob = datetime.fromisoformat(dob.replace("Z", "+00:00"))
                except Exception:
                    dob = None
            if isinstance(dob, datetime) and dob.tzinfo is not None:
                try:
                    dob = dob.astimezone(tz=timezone.utc).replace(tzinfo=None)
                except Exception:
                    pass

            params = [
                patient_id,
                data.get("firstName"),
                data.get("lastName"),
                dob,
                data.get("gender"),
                data.get("phone"),
                data.get("email"),
                data.get("address"),
                data.get("emergencyContact"),
                data.get("medicalHistory"),
                data.get("allergies"),
                data.get("bloodType")
            ]

            result = await self.execute_raw_query(query, params)
            if result:
                self.logger.info(f"Upserted patient: {result[0].get('id')}")
                return result[0]
            else:
                raise Exception("Failed to upsert patient - no result returned")

        except Exception as e:
            self.logger.error(f"Failed to upsert patient: {str(e)}")
            raise

    async def get_patient(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Get a patient by ID."""
        try:
            query = "SELECT * FROM patients WHERE id = $1"
            result = await self.execute_raw_query(query, [patient_id])
            return result[0] if result else None
        except Exception as e:
            self.logger.error(f"Failed to get patient {patient_id}: {str(e)}")
            raise

    async def list_patients(self, skip: int = 0, take: int = 100) -> List[Dict[str, Any]]:
        """List patients with pagination."""
        try:
            query = 'SELECT * FROM patients ORDER BY "createdAt" DESC LIMIT $1 OFFSET $2'
            return await self.execute_raw_query(query, [take, skip])
        except Exception as e:
            self.logger.error(f"Failed to list patients: {str(e)}")
            raise

    async def create_medicine(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new medicine."""
        try:
            query = """
                INSERT INTO medicines (
                    id, "subCategory", "productName", "saltComposition", "productPrice",
                    "productManufactured", "medicineDesc", "sideEffects", "drugInteractions", "createdAt", "updatedAt"
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW(), NOW())
                RETURNING *
            """

            import uuid
            med_id = str(uuid.uuid4())

            params = [
                med_id,
                data.get("subCategory"),
                data.get("productName"),
                data.get("saltComposition"),
                data.get("productPrice"),
                data.get("productManufactured"),
                data.get("medicineDesc"),
                data.get("sideEffects"),
                data.get("drugInteractions")
            ]

            result = await self.execute_raw_query(query, params)
            if result:
                self.logger.info(f"Created medicine: {result[0]['id']}")
                return result[0]
            else:
                raise Exception("Failed to create medicine")

        except Exception as e:
            self.logger.error(f"Failed to create medicine: {str(e)}")
            raise

    async def get_medicine_by_name(self, product_name: str) -> Optional[Dict[str, Any]]:
        """Get a medicine by product name."""
        try:
            query = 'SELECT * FROM medicines WHERE "productName" = $1'
            result = await self.execute_raw_query(query, [product_name])
            return result[0] if result else None
        except Exception as e:
            self.logger.error(f"Failed to get medicine {product_name}: {str(e)}")
            raise

    async def search_medicines(self, query: str, skip: int = 0, take: int = 50) -> List[Dict[str, Any]]:
        """Search medicines by name or description."""
        try:
            search_query = """
                SELECT * FROM medicines
                WHERE "productName" ILIKE $1
                   OR "medicineDesc" ILIKE $1
                   OR "saltComposition" ILIKE $1
                ORDER BY "productName"
                LIMIT $2 OFFSET $3
            """
            search_term = f"%{query}%"
            return await self.execute_raw_query(search_query, [search_term, take, skip])
        except Exception as e:
            self.logger.error(f"Failed to search medicines: {str(e)}")
            raise

    # Doctor operations
    async def create_doctor(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new doctor."""
        try:
            # Generate a simple ID (in production, use proper UUID generation)
            import uuid
            doctor_id = str(uuid.uuid4())

            query = """
                INSERT INTO doctors (
                    id, "firstName", "lastName", specialization, "licenseNumber",
                    phone, email, department, "yearsOfExperience", "createdAt", "updatedAt"
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW(), NOW())
                RETURNING id, "firstName", "lastName", specialization, "licenseNumber",
                         phone, email, department, "yearsOfExperience", "createdAt", "updatedAt"
            """

            params = [
                doctor_id,
                data.get('firstName'),
                data.get('lastName'),
                data.get('specialization'),
                data.get('licenseNumber'),
                data.get('phone'),
                data.get('email'),
                data.get('department'),
                data.get('yearsOfExperience')
            ]

            # Use execute_raw_query to handle the INSERT with RETURNING
            result = await self.execute_raw_query(query, params)

            if result:
                self.logger.info(f"Created doctor: {result[0]['firstName']} {result[0]['lastName']}")
                return result[0]
            else:
                raise Exception("Failed to create doctor - no result returned")

        except Exception as e:
            self.logger.error(f"Failed to create doctor: {str(e)}")
            raise

    async def upsert_doctor(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert or update a doctor based on unique licenseNumber (upsert)."""
        try:
            import uuid
            doctor_id = str(uuid.uuid4())

            query = """
                INSERT INTO doctors (
                    id, "firstName", "lastName", specialization, "licenseNumber",
                    phone, email, department, "yearsOfExperience", "createdAt", "updatedAt"
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW(), NOW())
                ON CONFLICT ("licenseNumber") DO UPDATE SET
                    "firstName" = EXCLUDED."firstName",
                    "lastName" = EXCLUDED."lastName",
                    specialization = EXCLUDED.specialization,
                    phone = EXCLUDED.phone,
                    email = EXCLUDED.email,
                    department = EXCLUDED.department,
                    "yearsOfExperience" = EXCLUDED."yearsOfExperience",
                    "updatedAt" = NOW()
                RETURNING id, "firstName", "lastName", specialization, "licenseNumber",
                          phone, email, department, "yearsOfExperience", "createdAt", "updatedAt"
            """

            params = [
                doctor_id,
                data.get('firstName'),
                data.get('lastName'),
                data.get('specialization'),
                data.get('licenseNumber'),
                data.get('phone'),
                data.get('email'),
                data.get('department'),
                data.get('yearsOfExperience')
            ]

            result = await self.execute_raw_query(query, params)
            if result:
                self.logger.info(f"Upserted doctor: {result[0]['firstName']} {result[0]['lastName']}")
                return result[0]
            else:
                raise Exception("Failed to upsert doctor - no result returned")

        except Exception as e:
            self.logger.error(f"Failed to upsert doctor: {str(e)}")
            raise

    async def get_doctor(self, doctor_id: str) -> Optional[Dict[str, Any]]:
        """Get a doctor by ID."""
        try:
            query = "SELECT * FROM doctors WHERE id = $1"
            result = await self.execute_raw_query(query, [doctor_id])
            return result[0] if result else None
        except Exception as e:
            self.logger.error(f"Failed to get doctor {doctor_id}: {str(e)}")
            raise

    # Placeholder methods for other operations
    async def create_appointment(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new appointment."""
        raise NotImplementedError("Appointment operations not yet implemented")

    async def get_appointments_by_patient(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get appointments for a patient."""
        raise NotImplementedError("Appointment operations not yet implemented")

    async def get_appointments_by_doctor(self, doctor_id: str, date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get appointments for a doctor."""
        raise NotImplementedError("Appointment operations not yet implemented")

    async def create_prescription(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new prescription."""
        raise NotImplementedError("Prescription operations not yet implemented")
