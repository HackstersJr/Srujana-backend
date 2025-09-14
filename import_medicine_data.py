#!/usr/bin/env python3
"""
Import Medicine Data from CSV to Prisma Database
"""

import asyncio
import csv
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from services.prisma_service import PrismaService


async def import_medicine_data(csv_path: str):
    """Import medicine data from CSV file."""
    logger = logging.getLogger(__name__)

    if not os.path.exists(csv_path):
        logger.error(f"CSV file not found: {csv_path}")
        return False

    try:
        logger.info(f"Importing medicine data from {csv_path}")

        prisma_service = PrismaService()
        await prisma_service.connect()

        imported_count = 0
        skipped_count = 0

        with open(csv_path, 'r', encoding='utf-8') as file:
            # Skip BOM if present
            if file.read(1) != '\ufeff':
                file.seek(0)

            reader = csv.DictReader(file)

            for row in reader:
                try:
                    # Clean and prepare data
                    medicine_data = {
                        "subCategory": row.get("sub_category", "").strip(),
                        "productName": row.get("product_name", "").strip(),
                        "saltComposition": row.get("salt_composition", "").strip() or None,
                        "productPrice": row.get("product_price", "").strip() or None,
                        "productManufactured": row.get("product_manufactured", "").strip() or None,
                        "medicineDesc": row.get("medicine_desc", "").strip() or None,
                        "sideEffects": row.get("side_effects", "").strip() or None,
                        "drugInteractions": row.get("drug_interactions", "").strip() or None,
                    }

                    # Skip if product name is empty
                    if not medicine_data["productName"]:
                        skipped_count += 1
                        continue

                    # Check if medicine already exists
                    existing = await prisma_service.get_medicine_by_name(medicine_data["productName"])
                    if existing:
                        logger.debug(f"Medicine already exists: {medicine_data['productName']}")
                        skipped_count += 1
                        continue

                    # Create medicine
                    await prisma_service.create_medicine(medicine_data)
                    imported_count += 1

                    # Log progress every 100 records
                    if imported_count % 100 == 0:
                        logger.info(f"Imported {imported_count} medicines...")

                except Exception as e:
                    logger.error(f"Failed to import medicine {row.get('product_name', 'Unknown')}: {str(e)}")
                    skipped_count += 1
                    continue

        await prisma_service.disconnect()

        logger.info(f"Import completed: {imported_count} imported, {skipped_count} skipped")
        return True

    except Exception as e:
        logger.error(f"Import failed: {str(e)}")
        return False


async def create_sample_data():
    """Create sample healthcare data for testing."""
    logger = logging.getLogger(__name__)

    try:
        logger.info("Creating sample healthcare data")

        prisma_service = PrismaService()
        await prisma_service.connect()

        # Sample lab tests
        lab_tests_data = [
            {
                "testName": "Complete Blood Count",
                "testCategory": "Hematology",
                "normalRange": "WBC: 4.5-11.0 K/μL, RBC: 4.5-5.9 M/μL",
                "unit": "Various",
                "description": "Comprehensive blood test that evaluates overall health and detects disorders"
            },
            {
                "testName": "Lipid Profile",
                "testCategory": "Cardiac",
                "normalRange": "Total Cholesterol: <200 mg/dL, HDL: >40 mg/dL",
                "unit": "mg/dL",
                "description": "Blood test to measure cholesterol and triglyceride levels"
            },
            {
                "testName": "Blood Glucose",
                "testCategory": "Metabolic",
                "normalRange": "70-100 mg/dL (fasting)",
                "unit": "mg/dL",
                "description": "Test to measure glucose levels in the blood"
            },
            {
                "testName": "Thyroid Function Test",
                "testCategory": "Endocrine",
                "normalRange": "TSH: 0.4-4.0 mIU/L, T3: 80-200 ng/dL",
                "unit": "Various",
                "description": "Test to evaluate thyroid gland function"
            }
        ]

        for test_data in lab_tests_data:
            # Check if test already exists (use camelCase column names matching Prisma schema)
            existing_tests = await prisma_service.execute_raw_query(
                'SELECT id FROM lab_tests WHERE "testName" = $1',
                [test_data["testName"]]
            )

            if not existing_tests:
                # Generate id for lab test to satisfy NOT NULL constraint
                import uuid
                lab_id = str(uuid.uuid4())

                await prisma_service.execute_raw_command(
                    'INSERT INTO lab_tests (id, "testName", "testCategory", "normalRange", "unit", "description", "createdAt", "updatedAt") VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())',
                    [
                        lab_id,
                        test_data["testName"],
                        test_data["testCategory"],
                        test_data["normalRange"],
                        test_data["unit"],
                        test_data["description"]
                    ]
                )

        await prisma_service.disconnect()

        logger.info("Sample data created successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to create sample data: {str(e)}")
        return False


async def main():
    """Main import function."""
    logging.basicConfig(level=logging.INFO)

    # Check if DATABASE_URL is set
    if not os.getenv("DATABASE_URL"):
        print("ERROR: DATABASE_URL environment variable is not set")
        sys.exit(1)

    # CSV file path
    csv_path = os.path.join(Path(__file__).parent.parent, "archive", "medicine_data.csv")

    print("Starting medicine data import...")

    # Import medicine data
    if not await import_medicine_data(csv_path):
        sys.exit(1)

    # Create sample data
    if not await create_sample_data():
        sys.exit(1)

    print("Data import completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
