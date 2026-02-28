"""
Configuration for deal finder v4 module.
"""

import os

from dotenv import load_dotenv

load_dotenv()

# Time window (in days) to look back for recently funded accounts.
# Accounts with Affinity_Last_Funding_Date__c within this window are considered "recently funded".
# TIME_DELTA_DAYS: int = 30
TIME_DELTA_DAYS: int = 365

# IO filtering: allowed initial impressions (keep only these)
ALLOWED_INITIAL_IMPRESSIONS: tuple = ("Average", "Strong")
# IO filtering: rejection keywords (exclude IOs where Reason_For_Passing__c contains any of these)
REJECTION_KEYWORDS: tuple = ("focus", "team", "old")

# Outbound team email recipients
OUTBOUND_EMAIL_RECIPIENTS: tuple = (
    "outbound@uvcpartners.com",
    "philipp.frauenstein@uvcpartners.com",
    "esteban.prado@uvcpartners.com",
)

# MongoDB connection (from .env)
MONGO_URI: str = os.environ["MONGO_URI"]
MONGO_DB_NAME: str = os.environ["MONGO_DB_NAME"]
MONGO_DB_COLLECTION_NAME: str = os.environ["MONGO_DB_COLLECTION_NAME"]
IO_COLLECTION_NAME: str = os.environ["IO_COLLECTION_NAME"]
RECOMMENDATION_STACK_COLLECTION_NAME: str = os.environ["RECOMMENDATION_STACK_COLLECTION_NAME"]


# Google Sheets: template to copy, destination folder, service account (from .env)
GOOGLE_SHEETS_TEMPLATE_ID: str = os.environ["GOOGLE_SHEETS_TEMPLATE_ID"]
GOOGLE_SHEETS_DESTINATION_FOLDER_ID: str = os.environ["GOOGLE_SHEETS_DESTINATION_FOLDER_ID"]
SERVICE_ACCOUNT_FILE: str = os.environ["SERVICE_ACCOUNT_FILE"]

