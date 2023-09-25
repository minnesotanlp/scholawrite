from flask import Flask
from flask_restx import Api, Resource, fields
import pymongo
from pymongo import MongoClient

application = Flask(__name__)
app = Api(app=application,
          version="1.0",
          title="ReWARD",
          description="Record Writer Actions for Rhetorical Adjustments")



name_space = app.namespace('ReWARD', description='Record writing activity')

model = app.model('Recording Writer Actions for Rhetorical Adjustment',
                  {'Reward': fields.String(required=True,
                                           description="--",
                                           help="--")})
                                           
client = MongoClient('mongo', 27017)
db = client.flask_db
activity = db.activity
user_data = db["user_data"]

project_IDs = db["project_IDs"]

MEMORY = 0

