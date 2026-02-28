import gspread
from google.oauth2.service_account import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build

from config import SERVICE_ACCOUNT_FILE
from lib.utils import *


# Define the scope and authenticate using google-auth library
scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scope)
client = gspread.authorize(credentials)

def update_worksheet_with_spreadsheet_id(spreadsheet_id, worksheet_name, dataframe):
    spreadsheet = client.open_by_key(spreadsheet_id)
    try:
        worksheet = spreadsheet.worksheet(worksheet_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=dataframe.shape[0] + 1,
                                              cols=dataframe.shape[1])

    # Update the worksheet with the dataframe data
    # worksheet.clear()
    worksheet.update([dataframe.columns.values.tolist()] + dataframe.values.tolist())

# Path to the service account key file
# Scopes required for the APIs
SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets']
# Authenticate and construct service
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=credentials)
sheets_service = build('sheets', 'v4', credentials=credentials)


# Function to copy Google Sheet
def copy_sheet(sheet_id, folder_id, new_title):
    try:
        # Create a copy directly in the destination folder.
        # Service accounts have no Drive storage; copying to SA's root fails with
        # "storage quota exceeded". Specifying parents creates the file in the
        # folder (using the folder owner's/Shared Drive's quota instead).
        copied_sheet = drive_service.files().copy(
            fileId=sheet_id,
            body={'name': new_title, 'parents': [folder_id]}
        ).execute()

        return copied_sheet.get('id')
    except Exception as e:
        print_log(f'An error occurred: {e}')
        return None