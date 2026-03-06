# Deal Finder

Fetches recently funded UVC accounts from MongoDB, filters IOs, and uploads results to Google Sheets.

## Quick Start

```bash
source .venv/bin/activate
python main.py
```

## Setup

1. Copy `env.example` to `.env` and fill in all values.
2. **Email**: Add `EMAIL_SENDER` and `EMAIL_APP_PASSWORD` (from your Gmail app password).
3. **Google Sheets OAuth** (one-time): Add `GOOGLE_OAUTH_CLIENT_SECRETS_B64` to `.env` (base64 of client secrets from Google Cloud Console), then run:
   ```bash
   python scripts/setup_google_oauth.py
   ```
   The script will print `GOOGLE_OAUTH_TOKEN_B64` to add to `.env`.

## GitHub Actions (Weekly Run)

The workflow runs every **Monday at 8:00 AM Germany time** (7:00 UTC). You can also trigger it manually from the Actions tab.

### Single secret: `ENV_FILE`

Add one secret in **Settings → Secrets and variables → Actions**:

| Secret | Description |
|--------|-------------|
| `ENV_FILE` | Contents of your `.env` file (copy-paste the entire file) |

The workflow writes this to `.env` before running, so all config (MongoDB, Google, email) comes from one place.
