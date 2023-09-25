from flask import request, jsonify
from flask_restx import Resource
import traceback
from rich.console import Console
from config import app, name_space, model, user_data, projectIds

@name_space.route("/ids")
class MainClass(Resource):
    @app.doc(responses={200: 'OK', 400: 'Invalid Argument', 500: 'Mapping Key Error'},
             params={'activity': 'data from most recent writing activity',
                     'timestamp': 'The time at which writer action was recorded'})
    @app.expect(model)
    def post(self):
        try:
            response = jsonify()
            if request.method == 'POST':
                info = request.get_json(force=True)
                if info["task"] == "getIDs":
                    user_ids = project_IDs.find({'username': info['username']})
                    response = jsonify({"status": 300, "project_IDs": user_ids[0]["project_IDs"]})
                    console.log({"status": 300, 'username': info['username'], "project_IDs": user_ids[0]["project_IDs"], "message": "project IDs send"})
                else:
                    collection_filter = {'username': info['username']}
                    new_values = {"$set": {'project_IDs': info['project_IDs']}}
                    project_IDs.update_one(collection_filter, new_values, upsert=True)
                    response = jsonify({"status": 300})
                    console.log({"status": 300, 'username': info['username'], 'project_IDs': info['project_IDs'], "message": "project IDs saved"})
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Credentials', 'true')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
            response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            return response
        except:
            print(traceback.print_exc())
            response = {"status": 400}
            response = jsonify(response)
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Credentials', 'true')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
            response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            return response
