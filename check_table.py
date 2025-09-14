#!/usr/bin/env python3

import asyncio
import sys
sys.path.append('.')
from services.prisma_service import PrismaService

async def check_table_structure():
    service = PrismaService()
    await service.connect()
    
    try:
        # Check the table structure
        query = "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'doctors' ORDER BY ordinal_position"
        result = await service.execute_raw_query(query)
        print('Doctors table columns:')
        for row in result:
            print(f"  {row['column_name']}: {row['data_type']}")
    except Exception as e:
        print('Error:', str(e))
        import traceback
        traceback.print_exc()
    finally:
        await service.disconnect()

if __name__ == "__main__":
    asyncio.run(check_table_structure())
