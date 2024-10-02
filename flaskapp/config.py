from pymongo import MongoClient, errors
import spacy
from flask import Flask
import os
from rich.console import Console
import diff_match_patch as dmp_module

try:
    sent_tokenizer = spacy.load("en_core_web_sm")
except OSError:
    os.system("spacy download en_core_web_sm")
    sent_tokenizer = spacy.load("en_core_web_sm")

dmp = dmp_module.diff_match_patch()

console = Console()

open_ai_key = ""

MEMORY = 0

app = Flask(__name__)

# for using Azure CosmoDB
def get_collection():
    # Get connection info from environment variables
    print("STARTING AGAIN")
    CONNECTION_STRING = os.getenv('CONNECTION_STRING')
    DB_NAME = os.getenv('DB_NAME')
    COLLECTION_NAME = os.getenv('COLLECTION_NAME')

    print("CONNECTION STRING: ", CONNECTION_STRING)
    print("DB NAME: ", DB_NAME)
    print("COLLECTION NAME: ", COLLECTION_NAME)

    # Create a MongoClient
    azure_client = MongoClient(CONNECTION_STRING)
    try:
        azure_client.server_info()  # validate connection string
    except errors.ServerSelectionTimeoutError:
        raise TimeoutError("Invalid API for MongoDB connection string or timed out when attempting to connect")

    azure_db = azure_client[DB_NAME]
    return azure_db[COLLECTION_NAME]


# create database instance
client = MongoClient('mongo', 27017)
db = client.flask_db
activity = db.activity
user_data = db["user_data"]
project_IDs = db["project_IDs"]
