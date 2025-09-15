#!/usr/bin/env python3

import asyncio
import sys
sys.path.append('.')
from services.prisma_service import PrismaService
import uuid

async def test_upsert_doctor():
    service = PrismaService()
    await service.connect()

    try:
        # Create a doctor with UPSERT syntax to handle duplicates
        doctor_id = str(uuid.uuid4())
        query = """
            INSERT INTO doctors (
                id, "firstName", "lastName", specialization, "licenseNumber",
                phone, email, department, "yearsOfExperience", "createdAt", "updatedAt"
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW(), NOW())
            ON CONFLICT ("licenseNumber") DO UPDATE SET
                "firstName" = EXCLUDED."firstName",
                "lastName" = EXCLUDED."lastName",
                "updatedAt" = NOW()
            RETURNING id, "firstName", "lastName", "licenseNumber"
        """

        params = [
            doctor_id, 'Dr. Sarah', 'Johnson', 'Cardiology', 'MD123456',
            '+1-555-0101', 'sarah.johnson@carecloud.com', 'Cardiology', 15
        ]

        result = await service.execute_raw_query(query, params)
        print('Doctor upserted successfully:', result)

    except Exception as e:
        print('Error:', str(e))
        import traceback
        traceback.print_exc()
    finally:
        await service.disconnect()

if __name__ == "__main__":
    asyncio.run(test_upsert_doctor())
