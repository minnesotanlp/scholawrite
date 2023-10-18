import os
import traceback
from flask import request, jsonify
from config import activity, app, console
from swtk import tokenize_copy, tokenize_revert, tokenize_paste, tokenize_keystroke, clean_up_info
from utils import context_tokenizer, call_chatgpt, update_database, form_data
from system import login, register
from ids import get_ids, set_ids


# def tokenize_paste(info):
#     # pre_text = sentence_reform(info["text"].splitlines(keepends=True))
#     # cur_text = sentence_reform(info["revision"].splitlines(keepends=True))
#     # pre = []
#     # cur = []
#     # for s in pre_text:
#     #     for each in sent_tokenizer(s).sents:
#     #         pre.extend([str(each)])
#     # for s in cur_text:
#     #     for each in sent_tokenizer(s).sents:
#     #         cur.extend([str(each)])
#     pre = info["text"].splitlines()
#     cur = info["revision"].splitlines()
#     if len(pre) < len(cur):
#         change = paste_handler(pre, cur, 1)
#     else:
#         change = paste_handler(pre, cur, 2)
#     if change != "All lines are the same":
#         char_num = paste_count_char(info["text"], info["revision"])
#         line_num = info['line']
#         revision = ['(' + str(line_num) + ',' + str(char_num) + ') ' + change]
#     else:
#         revision = ["All lines are the same"]
#
#     return revision

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
            state = info['state']
            onkey = info['onkey']
            if state == 2:
                info = tokenize_copy(info)
            elif state == 3:
                info["changes"] = tokenize_paste(info)
            elif onkey in "zZyY" and len(info['revision']) > 4:
                info["message"] = "UndoRedo"
                info["changes"] = tokenize_revert(info)
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
        return jsonify({'error': 'An error occurred'}), 500


@app.route("/paraphrase", methods=['POST', 'OPTIONS'])
def ai_paraphrase():
    try:
        info = request.get_json(force=True)
        state = info['message']
        #console.log(info)
        if request.method == 'OPTIONS':
            response = jsonify({'message': 'OK'})
        else:
            if state == "assist":
                context_dict = context_tokenizer(info)
                gpt_response = call_chatgpt(context_dict["selected_text"])
                update_database(activity, info, context_dict, gpt_response)
                data = form_data(context_dict, gpt_response, info["line"])
                console.log(data)
                response = jsonify(data)

            elif state == "user_selection":
                console.log(info)
                response = jsonify({"message": "received"})

            else:
                response = jsonify({"error": "Bad request"}), 400

        return response

    except Exception:
        console.log(traceback.print_exc())
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
        print(traceback.print_exc())
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
        print(traceback.print_exc())
        return jsonify({'error': 'An error occurred'}), 500


if __name__ == "__main__":
    ENVIRONMENT_DEBUG = os.environ.get("APP_DEBUG", False)
    ENVIRONMENT_PORT = os.environ.get("APP_PORT", 5000)
    app.run(host="0.0.0.0", port=ENVIRONMENT_PORT, debug=ENVIRONMENT_DEBUG)
