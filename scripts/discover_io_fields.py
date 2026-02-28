#!/usr/bin/env python3
"""
Helper script to discover field names from filtered_ios (or raw IO documents).

Run this to see which columns exist in your IO data, then use these field names
when configuring the display mapping in lib/io_column_mapping.py.

Usage:
    python scripts/discover_io_fields.py
    # or with venv: .venv/bin/python scripts/discover_io_fields.py

Requires .env with MONGO_URI, MONGO_DB_NAME, IO_COLLECTION_NAME, MONGO_DB_COLLECTION_NAME.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from pymongo import MongoClient

from config import IO_COLLECTION_NAME, MONGO_DB_COLLECTION_NAME, MONGO_DB_NAME, MONGO_URI, TIME_DELTA_DAYS
from main import get_recently_funded_accounts_from_mongo, get_filtered_ios_for_accounts


def discover_from_filtered_ios() -> list[str]:
    """
    Run the full pipeline to get filtered_ios and return its column names.
    Returns empty list if no IOs match the criteria.
    """
    accounts = get_recently_funded_accounts_from_mongo(time_delta_days=TIME_DELTA_DAYS)
    filtered_ios = get_filtered_ios_for_accounts(accounts)
    return list(filtered_ios.columns) if not filtered_ios.empty else []


def discover_from_raw_io_collection() -> set[str]:
    """
    Fetch a sample of raw IO documents from MongoDB and return all unique field names.
    Use when filtered_ios is empty (no accounts in time window).
    """
    client = MongoClient(MONGO_URI)
    try:
        db = client[MONGO_DB_NAME]
        io_collection = db[IO_COLLECTION_NAME]
        cursor = io_collection.find({}).limit(50)
        all_keys: set[str] = set()
        for doc in cursor:
            all_keys.update(doc.keys())
        return all_keys
    finally:
        client.close()


def main():
    print("Discovering IO field names...\n")

    # Try filtered_ios first (real pipeline output)
    print("1. Trying filtered_ios from pipeline...")
    cols = discover_from_filtered_ios()
    if cols:
        print("   Found columns from filtered_ios:\n")
        for i, c in enumerate(sorted(cols), 1):
            print(f"   {i:3}. {c}")
        print(f"\n   Total: {len(cols)} columns")
        return

    # Fallback: raw IO collection
    print("   (filtered_ios is empty, falling back to raw IO collection)\n")
    print("2. Fetching raw IO documents from MongoDB...")
    keys = discover_from_raw_io_collection()
    if keys:
        print("   Found fields in raw IO documents:\n")
        for i, k in enumerate(sorted(keys), 1):
            print(f"   {i:3}. {k}")
        print(f"\n   Total: {len(keys)} fields")
        print("\n   Note: Use these field names in lib/io_column_mapping.py for the display mapping.")
    else:
        print("   No documents found in IO collection. Check MONGO_URI and IO_COLLECTION_NAME.")


if __name__ == "__main__":
    main()
