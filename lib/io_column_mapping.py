"""
Display-name mapping for IO (Investment Opportunity) columns.

Maps human-readable column names for Google Sheets to possible source field names
from filtered_ios. Only fields that exist in the DataFrame will be included.

Run `python scripts/discover_io_fields.py` to discover available field names from
your MongoDB IO collection, then update this mapping if needed.
"""

from typing import Dict, List, Tuple

# Display name -> ordered list of possible source field names (first match wins).
# Updated from scripts/discover_io_fields.py output. Run it again if schema changes.
IO_DISPLAY_MAPPING: List[Tuple[str, List[str]]] = [
    ("Name", ["Name", "Name__c", "Account_Name_del_del__c"]),
    ("SF Description", ["Affinity_Description__c", "Short_Description__c"]),
    ("Country", ["Startup_Country__c", "Affinity_Location__c", "Startup_State_And_Country__c"]),
    ("Website", ["Website__c"]),
    ("Link to UVC IO in SF", ["Id"]),
    ("Date of Rejection in SF", ["r_rejected_out__c", "Rejection_Email_Sent__c"]),
    ("Initial Impression in SF", ["Initial_Impression__c"]),
    ("Reason for passing in SF", ["Reason_For_Passing__c"]),
    ("Advisor in SF", ["Advisor__c"]),
    ("SF IO Comment", ["Data_Team_Comment__c", "Fund_Comment__c"]),
    ("Account ID", ["Account__c"]),
    ("Last Funding Date", ["Affinity_Last_Funding_Date__c"]),
    ("Last Funding Amount (USD)", ["Affinity_Last_Funding_Amount_USD__c"]),
    ("Total Funding Amount (USD)", ["Affinity_Total_Funding_Amount_USD__c"]),
    ("Top 5 Investors", ["Affinity_Investors__c"]),
]


def build_valid_mapping(available_columns: List[str]) -> Dict[str, str]:
    """
    Build a mapping from display name to source column for columns that exist.

    Args:
        available_columns: Column names present in the DataFrame.

    Returns:
        Dict mapping display_name -> source_column for each valid mapping.
    """
    avail_set = set(available_columns)
    result: Dict[str, str] = {}
    for display_name, candidates in IO_DISPLAY_MAPPING:
        for candidate in candidates:
            if candidate in avail_set:
                result[display_name] = candidate
                break
    return result


def format_io_link(value: str) -> str:
    """Format Salesforce IO Id into Lightning URL."""
    if not value or value == "nan" or value == "":
        return ""
    base = "https://unternehmertum.lightning.force.com/lightning/r/Uvc_Investment_Opportunity__c"
    return f"{base}/{value}/view"
