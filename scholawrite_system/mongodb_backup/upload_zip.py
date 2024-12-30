import os
import sys

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow


AUTH_FOLDER = "./Auth_files/"
TOKEN_FILE = AUTH_FOLDER+"user_token.json"
CREDENTIAL_FILE = AUTH_FOLDER+"client_credential.json"
SCOPES = ["https://www.googleapis.com/auth/drive"]


def grant_permission_to_user_gdrive():
    creds = None
    # The file token.json stores the user's access token and refresh token. These are
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # credential_file allows this python program 
            # to request permission and receive consent to access user's google data.
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIAL_FILE, SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
    
    return creds


def upload_to_gdrive(gfolder_id, filename, mimetype, creds):
    try:
        # create drive api client
        service = build("drive", "v3", credentials=creds)

        file_metadata = {
            "name": filename,
            "mimeType": mimetype,
            "parents": [gfolder_id]
        }
        media = MediaFileUpload(filename, mimetype=mimetype, resumable=True)

        request = (
            service.files()
            .create(body=file_metadata, media_body=media, fields="id")
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print("Uploaded {0:.2f}%".format(status.progress() * 100))

        print(f'File with ID: "{response.get("id")}" has been uploaded.')

    except HttpError as error:
        print(f"An error occurred: {error}")
        response = None

    return response.get('id')


def main():
    gfolder_id = sys.argv[1]
    filename = sys.argv[2]
    mimetype = sys.argv[3]

    creds = grant_permission_to_user_gdrive()
    if creds:
        upload_to_gdrive(gfolder_id, filename, mimetype, creds)


if __name__ == "__main__":
    main()