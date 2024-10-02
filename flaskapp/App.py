import os
import traceback
from flask import request, jsonify
from config import activity, app, console
from swtk import tokenize_copy, tokenize_revert, tokenize_paste, tokenize_keystroke, clean_up_info
from utils import context_tokenizer, call_chatgpt, update_database, form_data
from system import login, register
from ids import get_ids, set_ids


import os.path
import re
import threading
from datetime import datetime, date
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
SAMPLE_SPREADSHEET_ID = "13gvKW7gmto4vsn-xBvqMqm2Kt8LoI8AQwlN5-x2y9a4"
SAMPLE_RANGE_NAME = "Q3:Q21"
TOKEN_FILE = "token.json"
CREDENTIAL_FILE = "sheet_credentials.json"
consented_projects = []
counter = 0

def fetch_google_sheet():
    creds = None
    global consented_projects, counter
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIAL_FILE, SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(TOKEN_FILE, "w") as token:
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

        # distinct_Projects = activity.distinct("project")
        # unconsent_projects = []
        # for each in distinct_Projects:
        #     if each not in consented_projects:
        #         unconsent_projects.append(each)
                    

        # console.log("number of unconsented projects: ",  len(unconsent_projects))
        # console.log(unconsent_projects)

        # for delete_ids in unconsent_projects:
        #     activity.delete_many({"project": delete_ids})

    except:
        traceback.print_exc()

    timer = threading.Timer(60, fetch_google_sheet)
    timer.start()


@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    return response


@app.route("/activity", methods=['POST', 'OPTIONS'])
def process_writer_actions():
    try:
        if request.method == 'OPTIONS':
            response = jsonify({'message': 'OK'})
        else:
            info = request.get_json(force=True)
            # if line == -1, means we didn't found the editing line
            try:
                temp_line = info['line']
            except:
                console.log(info)
                info['line'] = -1
            state = info['state']
            onkey = info['onkey']
            try:
                message = info['message']
            except:
                console.log(info)
                info['message'] = "No Message"
                message = info['message']

            if state == 2:
                info = tokenize_copy(info)
            elif state == 3:
                info["changes"] = tokenize_paste(info)
            elif (onkey in "zZyY" or message == "Undoredo") and len(info['revision']) > 4:
                info["message"] = "UndoRedo"
                info["changes"] = tokenize_revert(info)
            else:
                info["changes"] = tokenize_keystroke(info)

            # add document to database
            clean_up_info(info, state)
            if info["project"] in consented_projects:
                activity.insert_one(info)
            else:
                console.log(info["project"])
            response = jsonify({"status": "Updated recent writing actions in doc"})
        return response

    except Exception:
        console.log(info)
        traceback.print_exc()
        return jsonify({'error': 'An error occurred'}), 500


@app.route("/paraphrase", methods=['POST', 'OPTIONS'])
def ai_paraphrase():
    try:
        if request.method == 'OPTIONS':
            response = jsonify({'message': 'OK'})
        else:
            info = request.get_json(force=True)
            state = info['message']
            if state == "assist":
                context_dict = context_tokenizer(info)
                gpt_response = call_chatgpt(context_dict["selected_text"])
                if info["project"] in consented_projects:
                    updated_info = update_database(activity, info, context_dict, gpt_response)
                else:
                    console.log(info["project"])
                data = form_data(context_dict, gpt_response, info["line"])
                response = jsonify(data)
                
            elif state == "user_selection":
                if info["project_id"] in consented_projects:
                    activity.insert_one(info)
                else:
                    console.log(info["project_id"])
                response = jsonify({"message": "received"})

            else:
                response = jsonify({"error": "Bad request"}), 400

        return response

    except Exception:
        console.log(info)
        traceback.print_exc()
        return jsonify({'error': 'An error occurred'}), 500


@app.route("/users", methods=['POST', 'OPTIONS'])
def users():
    try:
        if request.method == 'OPTIONS':
            response = jsonify({'message': 'OK'})
        else:
            info = request.get_json(force=True)
            state = info['state']
            if state == "login":
                code = login(info['username'], info['password'])
                data = {
                    "status": code
                }
                response = jsonify(data)
                console.log(data)

            elif state == "register":
                code = register(info['username'], info['password'])
                data = {
                    "status": code
                }
                response = jsonify(data)
                console.log(data)
            else:
                response = jsonify({"error": "Bad request"}), 400
        return response

    except Exception:
        traceback.print_exc()
        return jsonify({'error': 'An error occurred'}), 500


@app.route("/ids", methods=['POST', "OPTIONS"])
def post():
    try:
        if request.method == 'OPTIONS':
            response = jsonify({'message': 'OK'})
        else:
            info = request.get_json(force=True)
            if info["task"] == "getIDs":
                response = get_ids(info["username"])
            elif info["task"] == "setIDs":
                response = set_ids(info["username"], info["project_IDs"])
            else:
                response = jsonify({"error": "Bad request"}), 400
        return response

    except Exception:
        console.log(info)
        traceback.print_exc()
        return jsonify({'error': 'An error occurred'}), 500


current_time = datetime.now()
time_interval_seconds = 60
time_offset_seconds = time_interval_seconds - (current_time.second)
timer = threading.Timer(time_offset_seconds, fetch_google_sheet)
timer.start()


if __name__ == "__main__":
    ENVIRONMENT_DEBUG = os.environ.get("APP_DEBUG", False)
    ENVIRONMENT_PORT = os.environ.get("APP_PORT", 5000)
    app.run(host="localhost", port=ENVIRONMENT_PORT, debug=ENVIRONMENT_DEBUG)
