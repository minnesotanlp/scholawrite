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


def data_collection_overview():
    project_ids = []
    all_projects_times = []
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

    console.log("Total number of collected edits:", collection.count_documents({}))
    console.log("Total number of collected projects:", len(distinct_Projects))
    console.log("Average collected edits:", collection.count_documents({}) / len(distinct_Projects))
    most_project = collection.find_one(sort=[("project", -1)])
    least_project = collection.find_one(sort=[("project", 1)])
    console.log("Project with most recorded edits:", most_project)
    console.log("Project with least recorded edits:", least_project)
    most_user = collection.find_one(sort=[("username", -1)])
    least_user = collection.find_one(sort=[("username", 1)])
    console.log("User with most recorded edits:", most_user)
    console.log("User with least recorded edits:", least_user)
    # Convert all timestamps to date objects for each project
    console.log(collection.distinct("username"))

    for i in range(len(all_projects_times)):
        time_list = []
        for project_time in all_projects_times[i]:
            time_list.append(datetime.fromtimestamp(project_time))

        # Find the earliest and latest dates
        min_date = min(time_list).date()
        max_date = max(time_list).date()
        console.log(project_ids[i], "   ", min_date, "  ", max_date, "  ",
                    collection.count_documents({"project": project_ids[i]}))
        console.log(collection.find({"project": project_ids[i]}).distinct("username"))


def change_project_overview():
    project_ids = []
    all_projects_times = []
    time_list = []
    temp_data = {}
    global dates

    # Get all projects and their corresponding timestamps
    distinct_Projects = collection.distinct("project")
    distinct_Projects = list(filter(None, distinct_Projects))
    # temp = {}

    # # Find latest edit time of each project
    # for project in distinct_Projects:
    #     latest_time_document = collection.find_one({"project": project}, {"sort": {"timestamp": -1 }})
    #     temp[project] = collection.find_one(latest_time_document)["timestamp"]

    # # Sorting the dictionary based on time in decending order
    # sorted_temp = dict(sorted(temp.items(), key=lambda item: item[1], reverse=True))

    # distinct_Projects = list(sorted_temp.keys())
    # console.log(distinct_Projects)

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
        all_projects_times.append(timestamps)

    # Convert all timestamps to date objects for each project
    for i in range(len(all_projects_times)):
        time_list = []
        for project_time in all_projects_times[i]:
            time_list.append(datetime.fromtimestamp(project_time))

        # Find the earliest and latest dates
        min_date = min(time_list).date()
        max_date = max(time_list).date()
        # Generate date strings and initialize counts
        days = ((max_date - min_date).days // 15 + 1) * 15
        date_strings = [(min_date + timedelta(days=i)).strftime('%b %d') for i in
                        range(days)]
        counts = [0] * len(date_strings)

        usernames = ""
        # Count the occurrences of each date
        for dt in time_list:
            index = (dt.date() - min_date).days
            counts[index] += 1
        for username in collection.find({"project": project_ids[i]}).distinct("username"):
            usernames = usernames + username + "; "
        temp_data[project_ids[i]] = [usernames, date_strings, counts]
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


def generate(projectID, writer_action_idx, writer_action_offset):
    actions = []
    diffs_htmls = []
    users = []
    overall_htmls = []
    data = collection.find({'project': projectID})
    num_action_send = min(writer_action_offset, collection.count_documents({'project': projectID}) - writer_action_idx,
                          50)

    for j in range(writer_action_idx, writer_action_idx + num_action_send):
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
    return writer_action_idx, writer_action_idx + num_action_send, info


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
            writer_action_idx = info["writer_action_idx"]
            writer_action_offset = info["writer_action_offset"]

            if collection.count_documents({'project': projectID}) > writer_action_idx:
                min_idx, max_idx, info = generate(projectID, writer_action_idx, writer_action_offset)
            else:
                min_idx = -1
                max_idx = -1
                info = [{"action": {"file": "400 Error", "text": "POST /create: Invalid Index",
                                    "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')},
                         "htmls": "POST /create: Invalid Index. The index you entered either too small or too large.",
                         "user": "Server"}]
            response = {"min": min_idx, "max": max_idx, "status": "ok", "info": info}
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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5200)
