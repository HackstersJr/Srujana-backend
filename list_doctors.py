import asyncio
import sys

sys.path.append('.')
from services.prisma_service import PrismaService


async def list_doctors():
    service = PrismaService()
    await service.connect()
    try:
        query = 'SELECT "firstName", "lastName" FROM doctors ORDER BY "lastName", "firstName"'
        results = await service.execute_raw_query(query)
        if not results:
            print('No doctors found')
            return
        print('Doctors:')
        for r in results:
            print(f"- {r.get('firstName')} {r.get('lastName')}")
    except Exception as e:
        print('Error:', str(e))
    finally:
        await service.disconnect()


if __name__ == '__main__':
    asyncio.run(list_doctors())
