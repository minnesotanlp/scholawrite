import traceback
from flask import request, jsonify, render_template, redirect
from config import activity, app, console
from swtk import tokenize_copy, tokenize_revert, tokenize_paste, tokenize_keystroke, clean_up_info
from utils import context_tokenizer, call_chatgpt, update_database, form_data
from system import login, register, does_exist, update_password

import os.path
import threading
import random
from datetime import datetime, timedelta
from gcloud import fetch_google_sheet, gmail_send_message, consented_projects

recovery_dict = {}


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
            # if line == -1, means we didn't find the editing line
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
                    update_database(activity, info, context_dict, gpt_response)
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


@app.route('/forgot_password', methods=['POST'])
def forgot_password():
    try:
        info = request.get_json(force=True)
        email = info['email']
        if does_exist(email):
            hashed_path = str(abs(hash(email + str(random.randint(0, 1000)))))
            recovery_dict[email] = [hashed_path, datetime.now()]
            recovery_url = "http://127.0.0.1:5000/reset_password/" + hashed_path
            gmail_send_message(email, recovery_url)
        return {"status": 300}

    except Exception:
        traceback.print_exc()
        return {"status": 500}


def get_entry(hashed_path):
    for entry in recovery_dict.items():
        if entry[1][0] == hashed_path:
            return entry
    return None


@app.route('/reset_password/<hashed_path>', methods=['GET', 'POST'])
def reset_password(hashed_path):
    # check if hashed_path exist in our dictionary.
    # If so, get corresponding email and date object
    entry = get_entry(hashed_path)
    if entry:
        # if the time is valid, we process the recovery password requests
        start_time = entry[1][1]
        target_email = entry[0]
        if (datetime.now() - start_time) <= timedelta(minutes=30):
            if request.method == 'POST':
                try:
                    new_pass = request.form["new_pass"]
                    update_password(target_email, new_pass)
                    # Recovery complete, remove email from recovery dictionary
                    del recovery_dict[target_email]
                    return redirect('/reset_success')
                except:
                    del recovery_dict[target_email]
                    return redirect('/reset_fail')
            else:
                return render_template("index.html")
        # if the time expired, delete the item from dictionary
        else:
            del recovery_dict[hashed_path]

    # These statements will be reach if email is not found or recovery time is expired
    response = {
        "error": "Not Found",
        "message": "The requested URL was not found on the server."
    }
    return jsonify(response), 404


@app.route('/reset_success', methods=['GET'])
def reset_success():
    return render_template("form_success.html")


@app.route('/reset_fail', methods=['GET'])
def reset_fail():
    return render_template("form_fail.html")


current_time = datetime.now()
time_interval_seconds = 60
time_offset_seconds = time_interval_seconds - (current_time.second)
timer = threading.Timer(time_offset_seconds, fetch_google_sheet)
timer.start()


if __name__ == "__main__":
    ENVIRONMENT_DEBUG = os.environ.get("APP_DEBUG", False)
    ENVIRONMENT_PORT = os.environ.get("APP_PORT", 5000)
    app.run(host="localhost", port=ENVIRONMENT_PORT, debug=ENVIRONMENT_DEBUG)
