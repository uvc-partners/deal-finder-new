import time
import pandas as pd

from config import (
    GOOGLE_AUTH_MODE,
    GOOGLE_IMPERSONATE_USER,
    GOOGLE_OAUTH_CLIENT_SECRETS_B64,
    GOOGLE_OAUTH_TOKEN_B64,
    SERVICE_ACCOUNT_B64,
    SERVICE_ACCOUNT_FILE,
)
from lib.google_auth import build_drive_and_sheets_services, get_credentials
from lib.utils import print_log


def _get_services():
    """Build Drive and Sheets services using configured auth."""
    creds = get_credentials(
        auth_mode=GOOGLE_AUTH_MODE,
        service_account_file=SERVICE_ACCOUNT_FILE or None,
        service_account_b64=SERVICE_ACCOUNT_B64 or None,
        impersonate_user=GOOGLE_IMPERSONATE_USER or None,
        oauth_client_secrets_b64=GOOGLE_OAUTH_CLIENT_SECRETS_B64 or None,
        oauth_token_b64=GOOGLE_OAUTH_TOKEN_B64 or None,
    )
    return build_drive_and_sheets_services(creds)


# Lazy init: build services on first use
_drive_service = None
_sheets_service = None


def _drive():
    global _drive_service, _sheets_service
    if _drive_service is None:
        _drive_service, _sheets_service = _get_services()
    return _drive_service


def _sheets():
    global _drive_service, _sheets_service
    if _sheets_service is None:
        _drive_service, _sheets_service = _get_services()
    return _sheets_service

# Chunk size for writes (avoids API timeouts on large datasets)
_CHUNK_SIZE = 500
# Delay between chunks to avoid rate limiting (seconds)
_CHUNK_DELAY = 0.5
# Max retries for transient failures
_MAX_RETRIES = 3


def _sanitize_value(val) -> str:
    """Convert cell value to string, handling NaN/None/np.nan."""
    if pd.isna(val):
        return ""
    return str(val)


def _ensure_worksheet_exists(spreadsheet_id: str, worksheet_name: str) -> None:
    """Create the worksheet if it does not exist."""
    spreadsheet = (
        _sheets().spreadsheets()
        .get(spreadsheetId=spreadsheet_id)
        .execute()
    )
    sheet_titles = [s["properties"]["title"] for s in spreadsheet.get("sheets", [])]
    if worksheet_name in sheet_titles:
        return
    request = {
        "requests": [{"addSheet": {"properties": {"title": worksheet_name}}}]
    }
    _sheets().spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body=request
    ).execute()
    print_log(f"Created worksheet '{worksheet_name}'")


def update_worksheet_with_spreadsheet_id(
    spreadsheet_id: str, worksheet_name: str, dataframe: pd.DataFrame
) -> None:
    """
    Write DataFrame to a Google Sheets worksheet using the Sheets API.
    Uses chunked writes and retries for reliability.
    """
    if dataframe.empty:
        print_log("DataFrame is empty; skipping worksheet update.")
        return

    _ensure_worksheet_exists(spreadsheet_id, worksheet_name)

    # Quote sheet name for A1 notation if it contains spaces/special chars
    range_prefix = f"'{worksheet_name}'!" if " " in worksheet_name else f"{worksheet_name}!"

    # Prepare values: headers + rows, sanitize NaN/None
    headers = dataframe.columns.values.tolist()
    rows = [
        [_sanitize_value(v) for v in row]
        for row in dataframe.values.tolist()
    ]
    all_values = [headers] + rows

    for i in range(0, len(all_values), _CHUNK_SIZE):
        chunk = all_values[i : i + _CHUNK_SIZE]
        start_row = i + 1  # 1-based row in Sheets
        range_name = f"{range_prefix}A{start_row}"

        for attempt in range(_MAX_RETRIES):
            try:
                _sheets().spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id,
                    range=range_name,
                    valueInputOption="USER_ENTERED",
                    body={"values": chunk},
                ).execute()
                break
            except Exception as e:
                if attempt < _MAX_RETRIES - 1:
                    wait = 2 ** attempt
                    print_log(f"Retry {attempt + 1}/{_MAX_RETRIES} after error: {e}")
                    time.sleep(wait)
                else:
                    raise

        if i + _CHUNK_SIZE < len(all_values):
            time.sleep(_CHUNK_DELAY)


# Function to copy Google Sheet
def copy_sheet(sheet_id, folder_id, new_title):
    try:
        # Create a copy in the destination folder.
        # With OAuth: copy is owned by the authenticated user (their quota).
        # With service account + impersonation: copy is owned by impersonated user.
        copied_sheet = _drive().files().copy(
            fileId=sheet_id,
            body={'name': new_title, 'parents': [folder_id]}
        ).execute()

        return copied_sheet.get('id')
    except Exception as e:
        print_log(f'An error occurred: {e}')
        return None