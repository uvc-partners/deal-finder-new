"""
List field names from the deal-finder data pipeline.
Downloads SF + CB data from MongoDB and prints all available columns.
Run from project root: python scripts/list_mongo_fields.py
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.mongodb import download_data_from_mongo_db


def main():
    print("Downloading data from MongoDB...")
    df_sf = download_data_from_mongo_db(
        database_name="datapipeline", collection_name="df3-sf-processed-onlylatest"
    )
    df_cb = download_data_from_mongo_db(
        database_name="datapipeline", collection_name="df3-cb-processed-lastcrawl-raised-europe"
    )

    if df_sf.empty:
        print("df_sf is empty - no SF columns available")
    else:
        print("\n=== SF columns (df3-sf-processed-onlylatest) ===")
        for i, col in enumerate(sorted(df_sf.columns)):
            print(f"  {i+1:3}. {col}")

    if df_cb.empty:
        print("\ndf_cb is empty - no CB columns available")
    else:
        print("\n=== CB columns (df3-cb-processed-lastcrawl-raised-europe) ===")
        for i, col in enumerate(sorted(df_cb.columns)):
            print(f"  {i+1:3}. {col}")

    # Merged df has: all SF cols + all CB cols + matching_criteria
    merged_cols = sorted(
        set(c for c in df_sf.columns if c != "_id")
        | set(c for c in df_cb.columns if c != "_id")
        | {"matching_criteria"}
    )
    print("\n=== Merged columns (available for reformat_for_printing) ===")
    for i, col in enumerate(merged_cols):
        print(f"  {i+1:3}. {col}")


if __name__ == "__main__":
    main()
