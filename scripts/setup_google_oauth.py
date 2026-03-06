#!/usr/bin/env python3
"""
One-time setup: authenticate with a Google account and get OAuth token for .env.

Run this script once to authorize the app. It will:
1. Open your browser
2. Ask you to sign in (use uvc.data.team@gmail.com or dt@uvcpartners.com)
3. Print OAUTH_TOKEN_B64 for you to add to your .env file

The account you use must have Editor access to the destination folder
(GOOGLE_SHEETS_DESTINATION_FOLDER_ID). The copied sheets will be owned by that account.

Prerequisites:
- Add GOOGLE_OAUTH_CLIENT_SECRETS_B64 to your .env:
  1. Create OAuth 2.0 credentials in Google Cloud Console (deal-finder-backend project)
  2. APIs & Services > Credentials > Create Credentials > OAuth client ID
  3. Application type: Desktop app
  4. Download the JSON, then run: base64 -i client_secrets.json | tr -d '\\n'
  5. Add to .env: GOOGLE_OAUTH_CLIENT_SECRETS_B64=<paste>

  Or, if you have config/oauth_client_secrets.json, run:
  base64 -i config/oauth_client_secrets.json | tr -d '\\n'
"""

import base64
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()


def main():
    root = Path(__file__).resolve().parent.parent
    client_secrets_b64 = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRETS_B64")
    client_secrets_path = root / "config" / "oauth_client_secrets.json"

    if not client_secrets_b64 and not client_secrets_path.exists():
        print("Error: OAuth client secrets not found.")
        print()
        print("Add GOOGLE_OAUTH_CLIENT_SECRETS_B64 to your .env:")
        print("  1. Go to https://console.cloud.google.com/apis/credentials")
        print("  2. Select the deal-finder-backend project")
        print("  3. Create Credentials > OAuth client ID > Desktop app")
        print("  4. Download JSON, then: base64 -i client_secrets.json | tr -d '\\n'")
        print("  5. Add to .env: GOOGLE_OAUTH_CLIENT_SECRETS_B64=<paste>")
        sys.exit(1)

    print("Opening browser for Google sign-in...")
    print("Use the account that has Editor access to the destination folder.")
    print("(e.g. uvc.data.team@gmail.com or dt@uvcpartners.com)")
    print()

    from lib.google_auth import get_credentials

    creds = get_credentials(
        auth_mode="oauth",
        oauth_client_secrets=str(client_secrets_path) if client_secrets_path.exists() and not client_secrets_b64 else None,
        oauth_client_secrets_b64=client_secrets_b64 or None,
        oauth_token_b64=None,  # No token yet - will run flow
        oauth_run_flow_if_missing=True,
    )

    token_b64 = base64.b64encode(creds.to_json().encode("utf-8")).decode("ascii")
    print()
    print("=" * 60)
    print("Add this line to your .env file:")
    print("=" * 60)
    print(f"GOOGLE_OAUTH_TOKEN_B64={token_b64}")
    print("=" * 60)
    print()
    print("You can now run the main deal finder.")


if __name__ == "__main__":
    main()
