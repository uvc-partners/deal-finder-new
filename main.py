"""
Deal finder v1.4: Get all UVC accounts from MongoDB where the last funding date
was within the last time_delta days (default: 30).

Uses the salesforce_accounts collection in UVC_Master_DB.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import pandas as pd
from pymongo import MongoClient

from config import (
    ALLOWED_INITIAL_IMPRESSIONS,
    IO_COLLECTION_NAME,
    MONGO_DB_COLLECTION_NAME,
    MONGO_DB_NAME,
    MONGO_URI,
    OUTBOUND_EMAIL_RECIPIENTS,
    REJECTION_KEYWORDS,
    RECOMMENDATION_STACK_COLLECTION_NAME,
    TIME_DELTA_DAYS,
)
from lib.integrations import send_email_with_link, upload_to_google_sheets
from lib.io_column_mapping import build_valid_mapping, format_io_link, IO_DISPLAY_MAPPING


def get_recently_funded_accounts_from_mongo(
    time_delta_days: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch UVC accounts from MongoDB (salesforce_accounts collection) where
    Affinity_Last_Funding_Date__c falls within the last `time_delta_days` days.

    Args:
        time_delta_days: Number of days to look back. Defaults to TIME_DELTA_DAYS from config.

    Returns:
        List of account dicts from MongoDB.
    """
    days = time_delta_days if time_delta_days is not None else TIME_DELTA_DAYS

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    today_end = datetime.now(timezone.utc).replace(hour=23, minute=59, second=59, microsecond=999999)
    # ISO date strings for documents that store dates as strings (e.g. from JSON import)
    cutoff_str = cutoff_date.strftime("%Y-%m-%d")
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    client = MongoClient(MONGO_URI)
    try:
        db = client[MONGO_DB_NAME]
        collection = db[MONGO_DB_COLLECTION_NAME]

        # Query for accounts where Affinity_Last_Funding_Date__c is within the time window.
        # Supports both BSON date/datetime and ISO date strings (YYYY-MM-DD).
        filter_query = {
            "Affinity_Last_Funding_Date__c": {"$exists": True, "$ne": None},
            "$or": [
                {
                    "Affinity_Last_Funding_Date__c": {
                        "$gte": cutoff_date,
                        "$lte": today_end,
                    }
                },
                {
                    "Affinity_Last_Funding_Date__c": {
                        "$gte": cutoff_str,
                        "$lte": today_str,
                    }
                },
            ],
        }

        cursor = collection.find(filter_query).sort("Affinity_Last_Funding_Date__c", -1)
        accounts = list(cursor)

        # Convert ObjectId to string for JSON serialization if needed
        for a in accounts:
            if "_id" in a:
                a["_id"] = str(a["_id"])

        return accounts
    finally:
        client.close()


def _to_datetime(val: Any) -> Optional[datetime]:
    """Convert various date representations to datetime for comparison."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.replace(tzinfo=None) if val.tzinfo else val
    if isinstance(val, str):
        try:
            dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
            return dt.replace(tzinfo=None) if dt.tzinfo else dt
        except ValueError:
            try:
                return datetime.strptime(val[:10], "%Y-%m-%d")
            except (ValueError, IndexError):
                return None
    return None


def get_filtered_ios_for_accounts(accounts: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    For each account, fetch the latest Investment Opportunity from MongoDB and apply
    filters. Returns a DataFrame of IOs that pass all criteria.

    Criteria:
    - Latest IO per account (by LastModifiedDate)
    - Initial_Impression__c in ALLOWED_INITIAL_IMPRESSIONS
    - Follow_Up__c is null or in the past (exclude if in the future)
    - Reason_For_Passing__c does not contain REJECTION_KEYWORDS

    Args:
        accounts: List of account dicts (must have "Id" for Account Salesforce ID).

    Returns:
        pandas DataFrame of filtered IOs.
    """
    if not accounts:
        return pd.DataFrame()

    # Use "Id" for Salesforce Account ID (salesforce_accounts uses this)
    account_ids = [a.get("Id") for a in accounts if a.get("Id")]
    if not account_ids:
        return pd.DataFrame()

    client = MongoClient(MONGO_URI)
    try:
        db = client[MONGO_DB_NAME]
        io_collection = db[IO_COLLECTION_NAME]

        cursor = io_collection.find({"Account__c": {"$in": account_ids}}).sort(
            "LastModifiedDate", -1
        )

        # First occurrence per account is the latest (cursor is sorted by LastModifiedDate desc)
        latest_by_account: Dict[str, Dict[str, Any]] = {}
        for doc in cursor:
            acct_id = doc.get("Account__c")
            if acct_id and acct_id not in latest_by_account:
                # Convert ObjectId to string for JSON compatibility
                d = dict(doc)
                if "_id" in d:
                    d["_id"] = str(d["_id"])
                latest_by_account[acct_id] = d

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        filtered: List[Dict[str, Any]] = []

        for acct_id, io in latest_by_account.items():
            imp = io.get("Initial_Impression__c") or ""
            if imp not in ALLOWED_INITIAL_IMPRESSIONS:
                continue

            follow_up = _to_datetime(io.get("Follow_Up__c"))
            if follow_up is not None and follow_up > now:
                continue

            rejection = (io.get("Reason_For_Passing__c") or "").lower()
            if any(kw in rejection for kw in REJECTION_KEYWORDS):
                continue

            filtered.append(io)

        return pd.DataFrame(filtered)
    finally:
        client.close()


def _download_recommendation_stack() -> pd.DataFrame:
    """Download the recommendation stack from MongoDB as a DataFrame."""
    client = MongoClient(MONGO_URI)
    try:
        db = client[MONGO_DB_NAME]
        collection = db[RECOMMENDATION_STACK_COLLECTION_NAME]
        return pd.DataFrame(list(collection.find({})))
    finally:
        client.close()


def remove_already_recommended_ios(
    df: pd.DataFrame, df_recommendation_stack: pd.DataFrame
) -> pd.DataFrame:
    """
    Remove IOs whose Account__c is already in the recommendation stack.
    Same logic as remove_already_recommended_startups but using Account__c.
    """
    subset_cols = ["Account__c"]
    if not all(c in df.columns for c in subset_cols):
        return df
    if len(df_recommendation_stack) == 0:
        return df
    if "Account__c" not in df_recommendation_stack.columns:
        return df
    df_new = df[
        ~df.set_index(subset_cols).index.isin(
            df_recommendation_stack.set_index(subset_cols).index
        )
    ].reset_index(drop=True)
    return df_new


def reformat_for_google_sheets(df: pd.DataFrame) -> pd.DataFrame:
    """
    Reformat IO dataframe for display in Google Sheets: map columns to display names,
    fillna, and convert to string. Only uses source fields that exist in the DataFrame.
    See lib/io_column_mapping.py for the mapping config. Run scripts/discover_io_fields.py
    to discover available field names.
    """
    if df.empty:
        return df
    df_clean = df.fillna("").infer_objects(copy=False).astype(str)

    valid = build_valid_mapping(list(df_clean.columns))
    if not valid:
        # No mappings matched; return cleaned df as-is
        return df_clean

    df_new = pd.DataFrame()
    used_sources = set()

    for display_name, candidates in IO_DISPLAY_MAPPING:
        source = valid.get(display_name)
        if source is None:
            continue
        used_sources.add(source)
        col_data = df_clean[source].copy()
        # Format Id as Lightning URL for "Link to UVC IO in SF"
        if display_name == "Link to UVC IO in SF" and source == "Id":
            col_data = col_data.apply(lambda v: format_io_link(str(v)))
        df_new[display_name] = col_data

    # Append unmapped columns that weren't used as a source
    extra_cols = [c for c in df_clean.columns if c not in used_sources]
    if extra_cols:
        for c in extra_cols:
            df_new[c] = df_clean[c]

    return df_new


def _upload_recommendation_stack_to_mongodb(df: pd.DataFrame) -> None:
    """Upload recommendation stack to MongoDB. Handles datetime for compatibility."""
    if df.empty:
        return
    df_clean = df.copy()
    for col in df_clean.columns:
        if pd.api.types.is_datetime64_any_dtype(df_clean[col]):
            mask = pd.notna(df[col])
            new_col = pd.Series([None] * len(df_clean), dtype=object)
            if mask.any():
                new_col.loc[mask] = df[col].loc[mask].dt.to_pydatetime()
            df_clean[col] = new_col

    client = MongoClient(MONGO_URI)
    try:
        db = client[MONGO_DB_NAME]
        collection = db[RECOMMENDATION_STACK_COLLECTION_NAME]
        data = df_clean.to_dict(orient="records")
        collection.insert_many(data)
        print(f"Recommendation stack updated in MongoDB ({len(data)} documents).")
    finally:
        client.close()


def run():
    """CLI entry point: fetch recently funded accounts, get filtered IOs, and print summary."""
    accounts = get_recently_funded_accounts_from_mongo(time_delta_days=TIME_DELTA_DAYS)
    print(f"Found {len(accounts)} UVC accounts with last funding date within the last {TIME_DELTA_DAYS} days")

    filtered_ios = get_filtered_ios_for_accounts(accounts)
    print(f"Filtered IOs (latest per account, passing criteria): {len(filtered_ios)}")

    # --- Removing IOs that were already recommended ---
    print("Removing IOs that were already recommended...")
    df_recommendation_stack = _download_recommendation_stack()
    n_before = len(filtered_ios)
    if len(df_recommendation_stack) > 0:
        filtered_ios = remove_already_recommended_ios(filtered_ios, df_recommendation_stack)
        n_after = len(filtered_ios)
        print(f"Initial amount: {n_before}. Removed {n_before - n_after} IOs. New amount: {n_after}.")

    # --- Reformat Dataframe for Google Sheets ---
    print("Reformatting data for Google Sheets...")
    df_final = reformat_for_google_sheets(filtered_ios)
    print("Data reformatted!")

    # --- Upload Data to Google Sheets ---
    new_sheet_url = upload_to_google_sheets(df_final)
    if new_sheet_url:
        print(f"Link to the new sheet: {new_sheet_url}")

    # --- Send email with link to Google Sheets ---
    # send_to_outbound = input("Send email to outbound? Y/N: ")
    # if send_to_outbound == "y" or send_to_outbound == "Y":
    #     if new_sheet_url:
    #         send_email_with_link(
    #             list(OUTBOUND_EMAIL_RECIPIENTS),
    #             new_sheet_url,
    #             df_final,
    #         )

    #     df_recommendations = filtered_ios[["Account__c"]].copy()
    #     df_recommendations["df_v1_4_recommendation_date"] = datetime.today()
    #     _upload_recommendation_stack_to_mongodb(df_recommendations)
    #     print("Recommendation stack updated in MongoDB.")

if __name__ == "__main__":
    run()
