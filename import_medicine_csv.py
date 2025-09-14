#!/usr/bin/env python3
"""
Import medicine data from CSV file into PostgreSQL database.
Handles large CSV files with batch processing for efficiency.
"""

import csv
import os
import sys
from typing import List, Dict, Any
import asyncio
from pathlib import Path

# Add the project root to Python path
sys.path.append(str(Path(__file__).parent))

from services.prisma_service import PrismaService


class MedicineDataImporter:
    """Import medicine data from CSV into database."""

    def __init__(self, csv_file_path: str, batch_size: int = 1000, skip_duplicates: bool = True, clear_existing: bool = False):
        self.csv_file_path = csv_file_path
        self.batch_size = batch_size
        self.skip_duplicates = skip_duplicates
        self.clear_existing = clear_existing
        self.prisma_service = PrismaService()

    async def connect_db(self):
        """Connect to the database."""
        await self.prisma_service.connect()
        print("✅ Connected to database")

    async def clear_existing_data(self):
        """Clear all existing medicine data."""
        try:
            print("🗑️  Clearing existing medicine data...")
            await self.prisma_service.execute_raw_command("DELETE FROM medicines")
            print("✅ Existing data cleared successfully")
        except Exception as e:
            print(f"❌ Error clearing existing data: {e}")
            raise

    async def disconnect_db(self):
        """Disconnect from the database."""
        await self.prisma_service.disconnect()
        print("✅ Disconnected from database")

    def read_csv_header(self) -> List[str]:
        """Read and return CSV header."""
        with open(self.csv_file_path, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            header = next(reader)
            return header

    def map_csv_to_db_fields(self, csv_row: Dict[str, str]) -> Dict[str, Any]:
        """Map CSV fields to database fields."""
        return {
            'subCategory': csv_row.get('sub_category', '').strip(),
            'productName': csv_row.get('product_name', '').strip(),
            'saltComposition': csv_row.get('salt_composition', '').strip() or None,
            'productPrice': csv_row.get('product_price', '').strip() or None,
            'productManufactured': csv_row.get('product_manufactured', '').strip() or None,
            'medicineDesc': csv_row.get('medicine_desc', '').strip() or None,
            'sideEffects': csv_row.get('side_effects', '').strip() or None,
            'drugInteractions': csv_row.get('drug_interactions', '').strip() or None,
        }

    async def check_existing_medicine(self, product_name: str) -> bool:
        """Check if medicine already exists."""
        try:
            existing = await self.prisma_service.get_medicine_by_name(product_name)
            return existing is not None
        except Exception as e:
            print(f"❌ Error checking existing medicine: {e}")
            return False

    async def import_batch(self, batch: List[Dict[str, Any]]) -> tuple[int, int]:
        """Import a batch of medicine records."""
        success_count = 0
        error_count = 0

        for record in batch:
            try:
                product_name = record['productName']
                if not product_name:
                    print(f"⚠️  Skipping record with empty product name")
                    error_count += 1
                    continue

                # Check if medicine already exists (only if skip_duplicates is True)
                if self.skip_duplicates and await self.check_existing_medicine(product_name):
                    print(f"⚠️  Medicine '{product_name}' already exists, skipping")
                    error_count += 1
                    continue

                # Create new medicine record
                await self.prisma_service.create_medicine(record)
                success_count += 1

            except Exception as e:
                print(f"❌ Error importing record '{record.get('productName', 'Unknown')}': {e}")
                error_count += 1

        return success_count, error_count

    async def import_csv(self) -> tuple[int, int]:
        """Import all records from CSV file."""
        print(f"📁 Reading CSV file: {self.csv_file_path}")

        # Check if file exists
        if not os.path.exists(self.csv_file_path):
            raise FileNotFoundError(f"CSV file not found: {self.csv_file_path}")

        total_success = 0
        total_errors = 0
        batch_number = 1

        try:
            with open(self.csv_file_path, 'r', encoding='utf-8') as file:
                # Skip BOM if present (common in CSV files from Excel)
                if file.read(1) != '\ufeff':
                    file.seek(0)

                # Use DictReader for better field mapping
                reader = csv.DictReader(file)

                batch = []
                for row in reader:
                    # Map CSV fields to database fields
                    db_record = self.map_csv_to_db_fields(row)
                    batch.append(db_record)

                    # Process batch when it reaches the batch size
                    if len(batch) >= self.batch_size:
                        print(f"🔄 Processing batch {batch_number} ({len(batch)} records)...")
                        success, errors = await self.import_batch(batch)
                        total_success += success
                        total_errors += errors
                        batch = []
                        batch_number += 1

                # Process remaining records
                if batch:
                    print(f"🔄 Processing final batch {batch_number} ({len(batch)} records)...")
                    success, errors = await self.import_batch(batch)
                    total_success += success
                    total_errors += errors

        except Exception as e:
            print(f"❌ Error reading CSV file: {e}")
            raise

        return total_success, total_errors

    async def run_import(self):
        """Run the complete import process."""
        print("🚀 Starting medicine data import...")
        print(f"📊 Batch size: {self.batch_size}")
        print(f"📁 CSV file: {self.csv_file_path}")

        try:
            await self.connect_db()

            # Clear existing data if requested
            if self.clear_existing:
                await self.clear_existing_data()

            # Get total record count estimate
            with open(self.csv_file_path, 'r', encoding='utf-8') as file:
                # Skip BOM if present
                if file.read(1) == '\ufeff':
                    pass  # BOM already consumed
                else:
                    file.seek(0)  # No BOM, reset to beginning

                total_lines = sum(1 for _ in file)
                estimated_records = total_lines - 1  # Subtract header

            print(f"📊 Estimated records to import: {estimated_records:,}")
            print(f"🔄 Skip duplicates: {self.skip_duplicates}")
            print(f"🗑️  Clear existing: {self.clear_existing}")

            # Clear existing data if requested
            if self.clear_existing:
                await self.clear_existing_data()

            # Import data
            success_count, error_count = await self.import_csv()

            # Print summary
            print("\n" + "="*50)
            print("📊 IMPORT SUMMARY")
            print("="*50)
            print(f"✅ Successfully imported: {success_count:,} records")
            print(f"❌ Errors: {error_count:,} records")
            print(f"📈 Success rate: {(success_count/(success_count+error_count)*100):.1f}%" if (success_count+error_count) > 0 else "0%")

            if success_count > 0:
                print("🎉 Medicine data import completed successfully!")
            else:
                print("⚠️  No records were imported. Check for errors above.")

        except Exception as e:
            print(f"❌ Import failed: {e}")
            raise
        finally:
            await self.disconnect_db()


async def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description='Import medicine data from CSV')
    parser.add_argument('--csv-file', default='data/input/medicine_data copy.csv',
                       help='Path to CSV file (default: data/input/medicine_data copy.csv)')
    parser.add_argument('--batch-size', type=int, default=500,
                       help='Batch size for processing (default: 500)')
    parser.add_argument('--no-skip-duplicates', action='store_true',
                       help='Import all records even if they already exist')
    parser.add_argument('--clear-existing', action='store_true',
                       help='Clear all existing medicine data before import')

    args = parser.parse_args()

    # CSV file path
    csv_file = args.csv_file

    # Check if CSV file exists
    if not os.path.exists(csv_file):
        print(f"❌ CSV file not found: {csv_file}")
        sys.exit(1)

    # Create importer instance
    skip_duplicates = not args.no_skip_duplicates
    importer = MedicineDataImporter(
        csv_file,
        batch_size=args.batch_size,
        skip_duplicates=skip_duplicates,
        clear_existing=args.clear_existing
    )

    # Run import
    await importer.run_import()


if __name__ == "__main__":
    asyncio.run(main())
