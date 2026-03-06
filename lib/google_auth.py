"""
Google API authentication: supports OAuth (user account) and service account.

OAuth is recommended for Drive/Sheets when the destination folder is in a personal
or Workspace Drive (not Shared Drive). Service accounts created after April 2025
cannot own Drive items, causing storageQuotaExceeded on copy operations.

Use OAuth when:
- Copying to a folder in "My Drive" (personal or Workspace)
- The folder owner's org doesn't provide Shared Drives

Use service account + impersonation when:
- You have domain-wide delegation set up (Workspace admin must grant it)

Credentials can be provided via .env as base64-encoded JSON:
- GOOGLE_OAUTH_CLIENT_SECRETS_B64, GOOGLE_OAUTH_TOKEN_B64 (OAuth)
- SERVICE_ACCOUNT_B64 (service account)
"""

import base64
import json
import os
from typing import Optional, Union

from google.oauth2 import credentials as user_credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Scopes required for Drive and Sheets
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]


def _decode_b64_json(b64: str) -> dict:
    """Decode base64 string to JSON dict."""
    return json.loads(base64.b64decode(b64).decode("utf-8"))


def _get_oauth_credentials(
    client_secrets: Union[str, dict],
    token: Union[str, dict],
    *,
    run_flow_if_missing: bool = False,
) -> user_credentials.Credentials:
    """
    Load OAuth credentials from token, refreshing if expired.

    client_secrets: Path to client_secrets.json, or dict from decoded JSON.
    token: Path to token.json, or dict from decoded JSON.

    If run_flow_if_missing is True and no valid token exists, runs the OAuth flow
    (opens browser). Use False for headless/cron runs - run setup_google_oauth.py
    first to create the token.
    """
    from google.auth.transport.requests import Request

    creds = None
    token_from_dict = isinstance(token, dict) and len(token) > 0

    if isinstance(token, dict) and len(token) > 0:
        creds = user_credentials.Credentials.from_authorized_user_info(
            token, scopes=SCOPES
        )
    elif isinstance(token, str) and os.path.exists(token):
        creds = user_credentials.Credentials.from_authorized_user_file(
            token, scopes=SCOPES
        )

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            if not token_from_dict and isinstance(token, str):
                with open(token, "w") as f:
                    f.write(creds.to_json())
        elif run_flow_if_missing:
            from google_auth_oauthlib.flow import InstalledAppFlow

            if isinstance(client_secrets, dict):
                flow = InstalledAppFlow.from_client_config(
                    client_secrets, scopes=SCOPES
                )
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    client_secrets, scopes=SCOPES
                )
            creds = flow.run_local_server(port=0)
            if isinstance(token, str):
                with open(token, "w") as f:
                    f.write(creds.to_json())
        else:
            raise FileNotFoundError(
                "OAuth token not found. Run: python scripts/setup_google_oauth.py"
            )

    return creds


def get_credentials(
    auth_mode: str = "oauth",
    service_account_file: Optional[str] = None,
    service_account_b64: Optional[str] = None,
    impersonate_user: Optional[str] = None,
    oauth_client_secrets: Optional[str] = None,
    oauth_client_secrets_b64: Optional[str] = None,
    oauth_token_file: Optional[str] = None,
    oauth_token_b64: Optional[str] = None,
    oauth_run_flow_if_missing: bool = False,
):
    """
    Get credentials for Google Drive and Sheets APIs.

    Args:
        auth_mode: "oauth" or "service_account"
        service_account_file: Path to service account JSON (for service_account mode)
        service_account_b64: Base64 of service account JSON (alternative to file)
        impersonate_user: Email to impersonate (domain-wide delegation, service_account only)
        oauth_client_secrets: Path to OAuth client_secrets.json (for oauth mode)
        oauth_client_secrets_b64: Base64 of OAuth client_secrets JSON (alternative)
        oauth_token_file: Path to OAuth token.json (for oauth mode)
        oauth_token_b64: Base64 of OAuth token JSON (alternative)

    Returns:
        Credentials object for building API clients.
    """
    if auth_mode == "oauth":
        client_secrets: Union[str, dict, None] = None
        token: Union[str, dict, None] = None

        if oauth_client_secrets_b64:
            client_secrets = _decode_b64_json(oauth_client_secrets_b64)
        elif oauth_client_secrets:
            client_secrets = oauth_client_secrets

        if oauth_token_b64:
            token = _decode_b64_json(oauth_token_b64)
        elif oauth_token_file:
            token = oauth_token_file

        if not client_secrets:
            raise ValueError(
                "OAuth mode requires GOOGLE_OAUTH_CLIENT_SECRETS_B64 in .env "
                "(or oauth_client_secrets file path)"
            )
        if not token and not oauth_run_flow_if_missing:
            raise ValueError(
                "OAuth mode requires GOOGLE_OAUTH_TOKEN_B64 in .env. "
                "Run: python scripts/setup_google_oauth.py"
            )
        return _get_oauth_credentials(
            client_secrets,
            token,
            run_flow_if_missing=oauth_run_flow_if_missing,
        )

    if auth_mode == "service_account":
        if service_account_b64:
            info = _decode_b64_json(service_account_b64)
            creds = service_account.Credentials.from_service_account_info(
                info, scopes=SCOPES
            )
        elif service_account_file:
            creds = service_account.Credentials.from_service_account_file(
                service_account_file, scopes=SCOPES
            )
        else:
            raise ValueError(
                "Service account mode requires SERVICE_ACCOUNT_B64 or "
                "SERVICE_ACCOUNT_FILE in .env"
            )
        if impersonate_user:
            creds = creds.with_subject(impersonate_user)
        return creds

    raise ValueError(f"Unknown auth_mode: {auth_mode}")


def build_drive_and_sheets_services(credentials):
    """Build Drive and Sheets API service objects from credentials."""
    drive_service = build("drive", "v3", credentials=credentials)
    sheets_service = build("sheets", "v4", credentials=credentials)
    return drive_service, sheets_service
