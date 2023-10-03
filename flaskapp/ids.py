from config import project_IDs, console
from flask import jsonify


def get_ids(username):
    user_ids = project_IDs.find({'username': username})
    response = jsonify({"status": 300, "project_IDs": user_ids[0]["project_IDs"]})
    console.log({"status": 300, 'username': username, "project_IDs": user_ids[0]["project_IDs"],
                 "message": "project IDs send"})
    return response


def set_ids(username, project_ids):
    collection_filter = {'username': username}
    new_values = {"$set": {'project_IDs': project_ids}}
    project_IDs.update_one(collection_filter, new_values, upsert=True)
    response = jsonify({"status": 300})
    console.log({"status": 300, 'username': username, 'project_IDs': project_ids,
                 "message": "project IDs saved"})
    return response
