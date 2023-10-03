import os
import traceback
from flask import request, jsonify
from config import activity, app, console
from swtk import tokenize_copy, tokenize_revert, tokenize_paste, tokenize_keystroke, clean_up_info
from utils import context_tokenizer, call_chatgpt, update_database, form_data
from system import login, register


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
            console.log(info)
            state = info['state']
            onkey = info['onkey']
            if state == 2:
                info = tokenize_copy(info)
            elif onkey in "zZyY" and len(info['revision']) >= 4:
                info["changes"] = tokenize_revert(info)
            elif state == 3:
                info["changes"] = tokenize_paste(info)
            else:
                info["changes"] = tokenize_keystroke(info)

            # add document to database
            clean_up_info(info, state)
            activity.insert_one(info)
            console.log(info)

            response = jsonify({"status": "Updated recent writing actions in doc"})
        return response

    except Exception:
        console.log(traceback.print_exc())


@app.route("/paraphrase", methods=['POST', 'OPTIONS'])
def ai_paraphrase():
    info = request.get_json(force=True)
    console.log(info)
    state = info['state']
    if request.method == 'OPTIONS':
        response = jsonify({'message': 'OK'})
    else:
        if state == "assist":
            context_dict = context_tokenizer(info)
            gpt_response = call_chatgpt(context_dict["selected_text"])
            update_database(activity, info, context_dict, gpt_response)
            data = form_data(context_dict, gpt_response)

            response = jsonify(data)
        elif state == "user_selection":
            console.log(info)
            response = jsonify({"message": "received"})
        else:
            response = jsonify({"message": "unknown state"})

    return response


@app.route("/users", methods=['POST', 'OPTIONS'])
def users():
    try:
        info = request.get_json(force=True)
        state = info['state']
        if state == "login":
            code = login(info['username'], info['password'])
            data = {
                "status": code
            }
            response = jsonify(data)
            console.log(data)

            return response

        elif state == "register":
            code = register(info['username'], info['password'])
            data = {
                "status": code
            }
            response = jsonify(data)
            console.log(data)

            return response

    except Exception:
        print(traceback.print_exc())


if __name__ == "__main__":
    ENVIRONMENT_DEBUG = os.environ.get("APP_DEBUG", False)
    ENVIRONMENT_PORT = os.environ.get("APP_PORT", 5000)
    app.run(host="localhost", port=ENVIRONMENT_PORT, debug=ENVIRONMENT_DEBUG)
