from flask import Flask
from flask import request
from flask import jsonify
from pymongo import MongoClient
import bcrypt
from datetime import datetime, timedelta
import diff_match_patch as dmp_module
from rich.console import Console
console = Console()

dmp = dmp_module.diff_match_patch()
import traceback

app = Flask(__name__)

client = MongoClient('mongo', 27017)
db = client.flask_db

collection = db.activity
user_data = db["user_data"]
project_IDs = db["project_IDs"]

dates = {}

import os.path
import re
import threading

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
SAMPLE_SPREADSHEET_ID = "13gvKW7gmto4vsn-xBvqMqm2Kt8LoI8AQwlN5-x2y9a4"
SAMPLE_RANGE_NAME = "L3:L15"
TOKEN_FILE = "token.json"
CREDENTIAL_FILE = "sheet_credentials.json"

def fetch_google_sheet():
    creds = None
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

        consented_projects = []
        for row in values:
            console.log(row)
            consented_projects.extend(re.split(r',\s*', row[0]))

        consented_projects = set(consented_projects)
        console.log("number of consented projects: ", len(consented_projects))
        console.log(consented_projects)

        distinct_Projects = collection.distinct("project")
        unconsent_projects = []
        for each in distinct_Projects:
            if each not in consented_projects:
                frkp = collection.find({"project": each}).distinct("username")
                if ("ryankoo" not in frkp) and ("kooryan" not in frkp):
                    unconsent_projects.append(each)
                    

        console.log("number of unconsented projects: ",  len(unconsent_projects))
        console.log(unconsent_projects)

        for delete_ids in unconsent_projects:
            collection.delete_many({"project": delete_ids})

    except:
        traceback.print_exc()

    timer = threading.Timer(24*60*60, fetch_google_sheet)
    timer.start()

def change_project_overview():
    project_ids = []
    all_projects_times = []
    time_list = []
    temp_data = {}
    global dates

    # Get all projects and their corresponding timestamps
    distinct_Projects = collection.distinct("project")
    distinct_Projects = list(filter(None, distinct_Projects))
    for id in distinct_Projects:
        timestamps = []
        selected_documents = collection.find({"project": id})
        for doc in selected_documents:
            if isinstance(doc["timestamp"], int):
                timestamps.append(doc["timestamp"] // 1000)
            else:
                time_string = doc["timestamp"].split(" GMT")[0]
                date_time_format = "%a %b %d %Y %H:%M:%S:%f"
                dt = datetime.strptime(time_string, date_time_format)
                timestamps.append(int(dt.timestamp()))
        project_ids.append(id)
        console.log(id)
        all_projects_times.append(timestamps)
            
    console.log("Total number of collected edits:",collection.count_documents({}))
    console.log("Total number of collected projects:", len(distinct_Projects))
    console.log("Number of projects that can be listed:",len(project_ids))
    console.log("Average collected edits:",collection.count_documents({})/len(distinct_Projects))
    t = sorted(all_projects_times, key=len, reverse=True)
    console.log("Project with most recorded edits:", project_ids[all_projects_times.index(t[0])])
    console.log("Project with least recorded edits:", project_ids[all_projects_times.index(t[-1])])
    # Convert all timestamps to date objects for each project
    console.log(collection.distinct("username"))
    for i in range(len(all_projects_times)):
        time_list = []
        for project_time in all_projects_times[i]:
            time_list.append(datetime.fromtimestamp(project_time))

        # Find the earliest and latest dates
        min_date = min(time_list).date()
        max_date = max(time_list).date()
        console.log(project_ids[i], "   ", min_date, "  ", max_date, "  ", collection.count_documents({"project": project_ids[i]}))
        console.log(collection.find({"project": project_ids[i]}).distinct("username"))
        # Generate date strings and initialize counts
        days = ((max_date - min_date).days // 15 + 1) * 15
        date_strings = [(min_date + timedelta(days=i)).strftime('%b %d') for i in
                        range(days)]
        counts = [0] * len(date_strings)

        # Count the occurrences of each date
        for dt in time_list:
            index = (dt.date() - min_date).days
            counts[index] += 1

        temp_data[project_ids[i]] = [date_strings, counts]
    dates = temp_data


def diff_prettyHtml(diffs):
    """Convert a diff array into a pretty HTML report.

Args:
  diffs: Array of diff tuples.

Returns:
  HTML representation.
"""
    html = []
    for (op, data) in diffs:
        text = (
            data.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\n", "&para;<br>")
        )
        if op == 1:
            html.append('<ins style="background:#82E0AA;">%s</ins>' % text)
        elif op == -1:
            html.append('<del style="background:#F1948A;">%s</del>' % text)
        elif op == 2:
            html.append('<del style="background:#C39BD3;">%s</del>' % text)
        elif op == 0:
            html.append("<span>%s</span>" % text)
    return "".join(html)

def generate(projectID):
    actions = []
    diffs_htmls = []
    users = []
    overall_htmls = []
    data = collection.find({'project': projectID})
    # print(collection.find({'project': projectID}))
    for j in range(collection.count_documents({'project': projectID})):
        try:
            actions.append({"file": data[j]["file"], "text": data[j]['text'], "timestamp": data[j]["timestamp"]})
            users.append(data[j]['username'])
            # actions[index].append(data[j])
        except:
            users.append(data[j]['username'])
            actions.append(
                {"file": data[j]["file"], 'suggestion': data[j]['suggestion'], "timestamp": data[j]["timestamp"]})
    # print(actions[0]['text'])
    diffs_htmls = []
    for i in range(len(actions) - 1):
        try:
            if actions[i]['text'] != actions[i + 1]['text']:
                diffs = dmp.diff_main(actions[i]['text'], actions[i + 1]['text'])
                dmp.diff_cleanupSemantic(diffs)
                diffs_htmls.append(diff_prettyHtml(diffs))
        except:
            diffs_htmls.append("lol")
            print([key for key in actions[i + 1]])
    # overall_htmls.append(diffs_htmls)

    info = []
    print(len(users))
    print(len(actions))
    print(len(diffs_htmls))
    for i in range(0, len(users)):
        try:
            if i == 0:
                info.append({"users": users[i], "actions": actions[i], "htmls": actions[0]['text']})
            if i > 0:
                info.append({"users": users[i], "actions": actions[i], "htmls": diffs_htmls[i - 1]})
        except:
            break
    return info


def verify_password(password, stored_salt, stored_hash):
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), stored_salt)
    return hashed_password == stored_hash


class LocalStore:
    def __call__(self, f: callable):
        f.__globals__[self.__class__.__name__] = self
        return f


@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    return response


@app.route('/create', methods=('POST', 'OPTIONS'))
@LocalStore()
def create():
    try:
        print(request.method)
        if request.method == 'OPTIONS':
            response = jsonify(), 200
        elif request.method == 'POST':
            info = request.get_json(force=True)
            print("THIS IS THE REQUEST", info)
            projectID = info["projectID"]

            # project_ids, actions, overall_htmls = generate(projectID)
            info = generate(projectID)
            # print(info)
            # print(project_ids, actions, overall_htmls)
            response = {"status": "ok", "info": info}
            response = jsonify(response)

        return response
        # return {"status": "ok", "projectIDs": project_ids, "diff_htmls": overall_htmls}
    except:
        print(traceback.print_exc())
        response = {"status": "no", "projectIDs": "", "diff_htmls": ""}
        response = jsonify(response)
        return response


@app.route('/login', methods=('POST', 'OPTIONS'))
def login():
    try:
        if request.method == 'OPTIONS':
            response = jsonify(), 200
        else:
            info = request.get_json(force=True)
            try:
                result = user_data.find_one({"username": info['username']})
                console.log(result)
                if result is None:
                    code = 100
                else:
                    if verify_password(info['password'], result['salt'], result['hashed_password']):
                        code = 300
                    else:
                        code = 100
            except:
                print(traceback.print_exc())
                code = 400
            data = {
                "status": code
            }
            response = jsonify(data)
            print(data)

        return response
    except:
        print(traceback.print_exc())


@app.route('/list', methods=('POST', 'OPTIONS'))
def list_projects():
    try:
        if request.method == 'POST':
            change_project_overview()
            response = {
                "data": dates
            }
            response = jsonify(response)
        elif request.method == 'OPTIONS':
            response = jsonify(), 200

        return response
    except:
        print(traceback.print_exc())


@app.route('/handshake', methods=['POST', 'OPTIONS'])
def index():
    if request.method == 'POST':
        response = jsonify({'handshake_message': 'You Got it!'})
    elif request.method == 'OPTIONS':
        response = jsonify(), 200

    return response


current_time = datetime.now()
seconds_in_a_day = 24 * 60 * 60
seconds_until_midnight = seconds_in_a_day - (current_time.hour * 3600 + current_time.minute * 60 + current_time.second)
timer = threading.Timer(seconds_until_midnight, fetch_google_sheet)
timer.start()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5200)
