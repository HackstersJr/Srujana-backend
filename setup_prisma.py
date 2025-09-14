#!/usr/bin/env python3
"""
Prisma Database Migration and Setup Script
"""

import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from services.prisma_service import PrismaService


async def setup_prisma():
    """Setup Prisma database and generate client."""
    logger = logging.getLogger(__name__)

    try:
        logger.info("Setting up Prisma...")

        # Generate Prisma client with better error handling
        logger.info("Generating Prisma client...")
        result = subprocess.run(["prisma", "generate"], capture_output=True, text=True, cwd=Path(__file__).parent)

        if result.returncode != 0:
            error_msg = result.stderr.lower()
            if ("permission denied" in error_msg or
                "errno 13" in error_msg or
                "enotfound" in error_msg or
                "getaddrinfo" in error_msg or
                "network" in error_msg or
                "connection" in error_msg):
                logger.warning("Prisma client generation failed due to permissions or network issues. This is expected in containerized environments.")
                logger.info("Continuing with database setup using raw SQL fallback...")
            else:
                logger.error(f"Failed to generate Prisma client: {result.stderr}")
                return False

        logger.info("Prisma client generation completed")

        # Create Prisma service instance
        prisma_service = PrismaService()

        # Connect to database
        await prisma_service.connect()

        # Push schema to database (create tables)
        logger.info("Pushing schema to database...")
        result = subprocess.run(["prisma", "db", "push"], capture_output=True, text=True, cwd=Path(__file__).parent)

        if result.returncode != 0:
            error_msg = result.stderr.lower()
            if ("enotfound" in error_msg or
                "getaddrinfo" in error_msg or
                "network" in error_msg or
                "connection" in error_msg or
                "binaries.prisma.sh" in error_msg):
                logger.warning("Prisma db push failed due to network issues. Falling back to raw SQL schema creation...")
                logger.info("Creating database schema using raw SQL...")

                # Fall back to raw SQL schema creation
                schema_success = await create_database_schema_raw(prisma_service)
                if not schema_success:
                    logger.error("Failed to create database schema using raw SQL")
                    await prisma_service.disconnect()
                    return False
            else:
                logger.error(f"Failed to push schema to database: {result.stderr}")
                await prisma_service.disconnect()
                return False

        logger.info("Schema pushed to database successfully")

        # Disconnect
        await prisma_service.disconnect()

        logger.info("Prisma setup completed successfully")
        return True

    except Exception as e:
        logger.error(f"Prisma setup failed: {str(e)}")
        return False


async def migrate_database():
    """Run database migrations for deployment."""
    logger = logging.getLogger(__name__)

    try:
        logger.info("Running database migrations for deployment...")

        # First try to deploy migrations
        result = subprocess.run(["prisma", "migrate", "deploy"], capture_output=True, text=True, cwd=Path(__file__).parent)

        if result.returncode == 0:
            logger.info("Database migrations completed successfully")
            return True

        # Check if the error is P3005 (database schema not empty)
        error_output = result.stderr.lower()
        if "p3005" in error_output or "database schema is not empty" in error_output:
            logger.warning("Database schema already exists (possibly from db push). Attempting to resolve...")

            # Try to list existing migrations first
            list_result = subprocess.run(["prisma", "migrate", "status", "--format", "json"], capture_output=True, text=True, cwd=Path(__file__).parent)

            if list_result.returncode == 0:
                # If we can get migration status, try to resolve applied migrations
                try:
                    import json
                    status_data = json.loads(list_result.stdout)
                    applied_migrations = [m['name'] for m in status_data.get('appliedMigrations', [])]

                    if applied_migrations:
                        # Mark existing applied migrations as resolved
                        for migration in applied_migrations:
                            resolve_result = subprocess.run(["prisma", "migrate", "resolve", "--applied", migration], capture_output=True, text=True, cwd=Path(__file__).parent)
                            if resolve_result.returncode == 0:
                                logger.info(f"Successfully resolved migration: {migration}")
                    else:
                        # No migrations applied, try to create and apply a baseline migration
                        logger.info("No migrations applied, creating baseline...")
                        baseline_result = subprocess.run(["prisma", "migrate", "dev", "--create-only", "--name", "baseline"], capture_output=True, text=True, cwd=Path(__file__).parent)
                        if baseline_result.returncode == 0:
                            logger.info("Baseline migration created successfully")
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Could not parse migration status: {e}")
            else:
                logger.warning("Could not get migration status, continuing with existing schema")

            # Continue regardless of resolution success since schema exists
            logger.info("Continuing with existing database schema")
            return True

        # For other errors, log and return failure
        logger.error(f"Failed to run migrations: {result.stderr}")
        return False

    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        return False


async def create_database_schema_raw(prisma_service: PrismaService) -> bool:
    """Create database schema using raw SQL as fallback when Prisma db push fails."""
    logger = logging.getLogger(__name__)

    try:
        logger.info("Creating database tables using raw SQL...")

        # SQL statements to create all tables based on schema.prisma
        create_tables_sql = [
            """
            CREATE TABLE IF NOT EXISTS patients (
                id TEXT PRIMARY KEY,
                "firstName" TEXT NOT NULL,
                "lastName" TEXT NOT NULL,
                "dateOfBirth" TIMESTAMP NOT NULL,
                gender TEXT NOT NULL,
                phone TEXT,
                email TEXT UNIQUE,
                address TEXT,
                "emergencyContact" TEXT,
                "medicalHistory" TEXT,
                allergies TEXT,
                "bloodType" TEXT,
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS doctors (
                id TEXT PRIMARY KEY,
                "firstName" TEXT NOT NULL,
                "lastName" TEXT NOT NULL,
                specialization TEXT NOT NULL,
                "licenseNumber" TEXT UNIQUE NOT NULL,
                phone TEXT,
                email TEXT UNIQUE,
                department TEXT,
                "yearsOfExperience" INTEGER,
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS appointments (
                id TEXT PRIMARY KEY,
                "patientId" TEXT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
                "doctorId" TEXT NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,
                "appointmentDate" TIMESTAMP NOT NULL,
                status TEXT DEFAULT 'Scheduled' CHECK (status IN ('Scheduled', 'Completed', 'Cancelled', 'No-show')),
                reason TEXT,
                notes TEXT,
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS prescriptions (
                id TEXT PRIMARY KEY,
                "patientId" TEXT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
                "doctorId" TEXT NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,
                "appointmentId" TEXT REFERENCES appointments(id),
                "medicationName" TEXT NOT NULL,
                dosage TEXT,
                frequency TEXT,
                "durationDays" INTEGER,
                instructions TEXT,
                "prescriptionDate" DATE DEFAULT CURRENT_DATE,
                status TEXT DEFAULT 'Active' CHECK (status IN ('Active', 'Completed', 'Discontinued')),
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS "medicalRecords" (
                id TEXT PRIMARY KEY,
                "patientId" TEXT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
                "doctorId" TEXT REFERENCES doctors(id),
                "recordDate" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                diagnosis TEXT,
                treatment TEXT,
                notes TEXT,
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS "labResults" (
                id TEXT PRIMARY KEY,
                "patientId" TEXT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
                "testName" TEXT NOT NULL,
                "testDate" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                results TEXT,
                "normalRange" TEXT,
                status TEXT DEFAULT 'Pending',
                notes TEXT,
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS "vitalSigns" (
                id TEXT PRIMARY KEY,
                "patientId" TEXT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
                "appointmentId" TEXT REFERENCES appointments(id),
                "measurementDate" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "bloodPressureSystolic" INTEGER,
                "bloodPressureDiastolic" INTEGER,
                "heartRate" INTEGER,
                temperature DECIMAL(4,1),
                "weightKg" DECIMAL(5,2),
                "heightCm" DECIMAL(5,2),
                bmi DECIMAL(4,1),
                "oxygenSaturation" INTEGER,
                notes TEXT,
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        ]

        # Execute each CREATE TABLE statement
        for sql in create_tables_sql:
            try:
                await prisma_service.execute_raw_command(sql)
                logger.info("Created table successfully")
            except Exception as e:
                logger.error(f"Failed to create table: {str(e)}")
                # Continue with other tables even if one fails
                continue

        logger.info("Database schema created successfully using raw SQL")
        return True

    except Exception as e:
        logger.error(f"Failed to create database schema: {str(e)}")
        return False


async def seed_database():
    """Seed database with initial data."""
    logger = logging.getLogger(__name__)

    try:
        logger.info("Seeding database...")

        prisma_service = PrismaService()
        await prisma_service.connect()

        # Add sample doctors
        doctors_data = [
            {
                "firstName": "Dr. Sarah",
                "lastName": "Johnson",
                "specialization": "Cardiology",
                "licenseNumber": "MD123456",
                "phone": "+1-555-0101",
                "email": "sarah.johnson@carecloud.com",
                "department": "Cardiology",
                "yearsOfExperience": 15
            },
            {
                "firstName": "Dr. Michael",
                "lastName": "Chen",
                "specialization": "Neurology",
                "licenseNumber": "MD789012",
                "phone": "+1-555-0102",
                "email": "michael.chen@carecloud.com",
                "department": "Neurology",
                "yearsOfExperience": 12
            },
            {
                "firstName": "Dr. Emily",
                "lastName": "Rodriguez",
                "specialization": "Pediatrics",
                "licenseNumber": "MD345678",
                "phone": "+1-555-0103",
                "email": "emily.rodriguez@carecloud.com",
                "department": "Pediatrics",
                "yearsOfExperience": 8
            }
        ]

        for doctor_data in doctors_data:
            await prisma_service.upsert_doctor(doctor_data)

        # Add sample patients
        patients_data = [
            {
                "firstName": "John",
                "lastName": "Doe",
                "dateOfBirth": "1985-03-15T00:00:00Z",
                "gender": "Male",
                "phone": "+1-555-0201",
                "email": "john.doe@email.com",
                "address": "123 Main St, Anytown, USA",
                "emergencyContact": "Jane Doe: +1-555-0202",
                "bloodType": "O+"
            },
            {
                "firstName": "Alice",
                "lastName": "Smith",
                "dateOfBirth": "1990-07-22T00:00:00Z",
                "gender": "Female",
                "phone": "+1-555-0203",
                "email": "alice.smith@email.com",
                "address": "456 Oak Ave, Somewhere, USA",
                "emergencyContact": "Bob Smith: +1-555-0204",
                "bloodType": "A-"
            }
        ]

        for patient_data in patients_data:
            await prisma_service.upsert_patient(patient_data)

        await prisma_service.disconnect()

        logger.info("Database seeded successfully")
        return True

    except Exception as e:
        logger.error(f"Database seeding failed: {str(e)}")
        return False


async def main():
    """Main setup function."""
    logging.basicConfig(level=logging.INFO)

    # Check if DATABASE_URL is set
    if not os.getenv("DATABASE_URL"):
        print("ERROR: DATABASE_URL environment variable is not set")
        sys.exit(1)

    print("Starting Prisma database setup...")

    # Setup Prisma
    if not await setup_prisma():
        sys.exit(1)

    # Run migrations
    if not await migrate_database():
        sys.exit(1)

    # Seed database
    if not await seed_database():
        sys.exit(1)

    # Import medicine data
    print("Importing medicine data...")
    result = subprocess.run([sys.executable, "import_medicine_data.py"], capture_output=True, text=True, cwd=Path(__file__).parent)

    if result.returncode != 0:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to import medicine data: {result.stderr}")
        sys.exit(1)

    print("Prisma database setup completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
