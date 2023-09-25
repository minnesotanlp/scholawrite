from flask import request, jsonify
from flask_restx import Resource
import traceback
from rich.console import Console
import bcrypt
from config import app, name_space, model, user_data

@name_space.route("/system")
class MainClass(Resource):
    check = 0

    @app.doc(responses={200: 'OK', 400: 'Invalid Argument', 500: 'Mapping Key Error'},
             params={'activity': 'data from most recent writing activity',
                     'timestamp': 'The time at which writer action was recorded'})
    def get(self):
        try:
            summary = "retrieving the writing actions real time from user input into the overleaf editor"

            return {
                "state": summary
            }

        except KeyError as e:
            name_space.abort(500, e.__doc__, status="Could not retrieve information", statusCode="500")
        except Exception as e:
            name_space.abort(400, e.__doc__, status="Could not retrieve information", statusCode="400")

    @app.doc(responses={200: 'OK', 400: 'Invalid Argument', 500: 'Mapping Key Error'},
             params={'activity': 'data from most recent writing activity',
                     'timestamp': 'The time at which writer action was recorded'})
    @app.expect(model)
    def hash_password(self, password):
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
        return salt, hashed_password

    def verify_password(self, password, stored_salt, stored_hash):
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), stored_salt)
        return hashed_password == stored_hash

    def post(self):
        try:
            global code
            info = request.get_json(force=True)
            state = info['state']
            if state == "login":
                try:
                    result = user_data.find_one({"username": info['username']})
                    print(result)
                    if result == None:
                        code = 100
                    else:
                        if self.verify_password(info['password'], result['salt'], result['hashed_password']):
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
                console.log(data)
                print(data)
                response.headers.add('Access-Control-Allow-Origin', '*')
                response.headers.add('Access-Control-Allow-Credentials', 'true')
                response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
                response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
                return response

            elif state == "register":
                try:
                    result = user_data.find_one({"username": info['username']})
                    if result:
                        code = 200
                    else:
                        salt, hashed_password = self.hash_password(info['password'])
                        user_data.insert_one({"username": info['username'], "salt": salt, "hashed_password": hashed_password})
                        code = 300
                except:
                    code = 400
                data = {
                    "status": code
                }
                response = jsonify(data)
                console.log(data)
                print(data)
                response.headers.add('Access-Control-Allow-Origin', '*')
                response.headers.add('Access-Control-Allow-Credentials', 'true')
                response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
                response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
                return response

        except KeyError as e:
            name_space.abort(500, e.__doc__, status="Could not save information", statusCode="500")

        except Exception as e:
            print(traceback.print_exc())
            name_space.abort(400, e.__doc__, status="Could not save information", statusCode="400")

    def options(self):
        response = jsonify({'message': 'OK'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response
