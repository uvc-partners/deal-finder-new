"""
Integrations for deal finder v1.4: Google Sheets upload, email, and worksheet updates.
"""

import datetime
from pathlib import Path
from typing import List, Optional

import pandas as pd

from config import (
    GOOGLE_SHEETS_DESTINATION_FOLDER_ID,
    GOOGLE_SHEETS_TEMPLATE_ID,
)
from lib.google_sheets import copy_sheet, update_worksheet_with_spreadsheet_id
from lib.mail import get_html_file, replace_content_variables, send_email


def _get_current_week() -> str:
    """Return current ISO week number as string."""
    today = datetime.date.today()
    return str(today.isocalendar().week)


def _get_today_str() -> str:
    """Return today's date as YYYY-MM-DD."""
    return datetime.date.today().strftime("%Y-%m-%d")


def _asset_path(filename: str) -> str:
    """Return path to asset file, relative to project root."""
    root = Path(__file__).resolve().parent.parent
    return str(root / "assets" / filename)


def upload_to_google_sheets(df: pd.DataFrame) -> Optional[str]:
    """
    Copy the template Google Sheet to the destination folder, populate it with
    the dataframe, and return the new sheet URL.

    Args:
        df: DataFrame to write to the "Startups to revisit" worksheet.

    Returns:
        URL of the new sheet, or None if the operation failed.
    """
    print("Copying the template sheet in Google Drive.")
    year = datetime.date.today().year
    week = _get_current_week()
    new_sheet_title = f"{year}_CW{week}_Deal Finder v1.4"

    new_sheet_id = copy_sheet(
        GOOGLE_SHEETS_TEMPLATE_ID,
        GOOGLE_SHEETS_DESTINATION_FOLDER_ID,
        new_sheet_title,
    )

    if not new_sheet_id:
        print("Failed to copy template sheet.")
        return None

    new_sheet_url = f"https://docs.google.com/spreadsheets/d/{new_sheet_id}/edit"
    print(f"Link to the new sheet: {new_sheet_url}")

    print("Updating the new sheet with report data.")
    update_worksheet_with_spreadsheet_id(
        new_sheet_id, "All Highlighted Startups", df
    )
    print("New sheet with report data updated.")
    return new_sheet_url


def send_email_with_link(
    receiver_emails: List[str],
    google_sheet_url: str,
    df: pd.DataFrame,
) -> None:
    """
    Send an email to the outbound team with a link to the Google Sheet.
    Uses template_email_no_startups if df is empty, else template_email_outbound_team.

    Args:
        receiver_emails: List of email addresses.
        google_sheet_url: URL of the Google Sheet.
        df: DataFrame (used only to decide which template; empty -> no startups).
    """
    content_variables = {
        "date": _get_today_str(),
        "button_link": google_sheet_url,
    }

    if len(df) == 0:
        template = get_html_file(_asset_path("template_email_no_startups.html"))
    else:
        template = get_html_file(_asset_path("template_email_outbound_team.html"))

    html_content = replace_content_variables(template, content_variables)
    subject = "Data Team - Weekly Update for Outbound Team (v1.4)"

    print(f"Sending email to {receiver_emails}.")
    send_email(receiver_emails, subject, html_content)
    print("Email sent successfully.")
