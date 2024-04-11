from config import console
import traceback
import os.path
import re
import threading
from datetime import date
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.errors import HttpError

SHEET_SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
SAMPLE_SPREADSHEET_ID = "13gvKW7gmto4vsn-xBvqMqm2Kt8LoI8AQwlN5-x2y9a4"
SAMPLE_RANGE_NAME = "L3:L20"

MAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]

SHEET_TOKEN_FILE = "credentials/sheet_token.json"
GMAIL_TOKEN_FILE = "credentials/gmail_token.json"
CREDENTIAL_FILE = "credentials/credentials.json"
consented_projects = []
counter = 0

email_body = '''Dear participant,
        
Please ignore this email if you didn't request any password reset.

Please go to this URL and enter your new password. URL expired in 30 min.
Your password reset URL is : {0}

Best regard,
ScholaWrite team'''


def fetch_google_sheet():
    creds = None
    global consented_projects, counter
    # The file gmail_token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(SHEET_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(SHEET_TOKEN_FILE, SHEET_SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIAL_FILE, SHEET_SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(SHEET_TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    try:
        service = build("sheets", "v4", credentials=creds)

        # Call the Sheets API
        sheet = service.spreadsheets()
        result = (
            sheet.values()
            .get(spreadsheetId=SAMPLE_SPREADSHEET_ID, range=SAMPLE_RANGE_NAME)
            .execute()
        )
        values = result.get("values", [])

        if not values:
            console.log("No data found.")
            return

        for row in values:
            if row != []:
                consented_projects.extend(re.split(r',\s*', row[0]))

        consented_projects = list(set(consented_projects))

        if counter == 0:
            console.log(date.today())
            console.log("number of consented projects: ", len(consented_projects))
            console.log(consented_projects)
        elif counter == (24 * 60):
            counter = -1
        counter += 1

    except HttpError:
        traceback.print_exc()

    timer = threading.Timer(60, fetch_google_sheet)
    timer.start()


import base64
from email.message import EmailMessage
from googleapiclient.discovery import build


def gmail_send_message(email_address, reset_url):
    """Shows basic usage of the Gmail API.
     Lists the user's Gmail labels.
     """
    creds = None
    # The file gmail_token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(GMAIL_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(GMAIL_TOKEN_FILE, MAIL_SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIAL_FILE, MAIL_SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(GMAIL_TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    try:
        # create gmail api client
        service = build("gmail", "v1", credentials=creds)

        message = EmailMessage()

        # If is quite safe because it checks if email address in our database before sending.
        # Only sent to the user in our database.
        message.set_content(email_body.format(reset_url))

        message["To"] = email_address
        message["From"] = "wang9257@umn.edu"
        message["Subject"] = "NO REPLY: ScholaWrite Password Reset"

        # encoded message
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        create_message = {"raw": encoded_message}
        # pylint: disable=E1101
        send_message = (
            service.users()
            .messages()
            .send(userId="me", body=create_message)
            .execute()
        )
        console.log(f'Message Id: {send_message["id"]}')

    except HttpError as error:
        print(f"An error occurred: {error}")
        send_message = None

    return send_message
