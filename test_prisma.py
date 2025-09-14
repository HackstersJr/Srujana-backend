#!/usr/bin/env python3
"""
Test script for Prisma database operations
"""

import asyncio
import logging
import os
from services.prisma_service import PrismaService


async def test_prisma_operations():
    """Test basic Prisma operations."""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Check if DATABASE_URL is set
    if not os.getenv("DATABASE_URL"):
        print("ERROR: DATABASE_URL environment variable is not set")
        return

    try:
        logger.info("Testing Prisma operations...")

        prisma_service = PrismaService()
        await prisma_service.connect()

        # Test creating a patient
        patient_data = {
            "firstName": "Test",
            "lastName": "Patient",
            "dateOfBirth": "1990-01-01T00:00:00Z",
            "gender": "Male",
            "phone": "+1-555-0123",
            "email": "test.patient@example.com",
            "bloodType": "O+"
        }

        patient = await prisma_service.create_patient(patient_data)
        logger.info(f"Created patient: {patient.id}")

        # Test getting the patient
        retrieved_patient = await prisma_service.get_patient(patient.id)
        if retrieved_patient:
            logger.info(f"Retrieved patient: {retrieved_patient.firstName} {retrieved_patient.lastName}")
        else:
            logger.error("Failed to retrieve patient")

        # Test searching medicines
        medicines = await prisma_service.search_medicines("insulin", skip=0, take=5)
        logger.info(f"Found {len(medicines)} medicines containing 'insulin'")

        # Test raw query
        result = await prisma_service.execute_raw_query("SELECT COUNT(*) as count FROM patients")
        logger.info(f"Total patients: {result[0]['count']}")

        await prisma_service.disconnect()

        logger.info("Prisma operations test completed successfully")

    except Exception as e:
        logger.error(f"Prisma test failed: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(test_prisma_operations())
