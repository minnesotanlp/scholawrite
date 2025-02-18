from pymongo import MongoClient
from datetime import datetime
from dateutil.relativedelta import relativedelta
from flask import Flask, render_template, redirect, send_from_directory
from flask import request, session, jsonify
import json
from rich.console import Console
import re
from pylatexenc.latex2text import LatexNodes2Text
import threading

console = Console()
# client = MongoClient('localhost', 27017)
client = MongoClient('mongo', 27017)
db = client.flask_db
collection = db.visual_data
annotation = db.annotation

# Maybe not needed for admin page.
user_data = db["user_data"]
project_IDs = db["project_IDs"]

mili_a_day = 24 * 3600000


def _find_titles():
    i = 1
    for pid in collection.distinct("project", {"file": {"$exists": True},
                        "message": {"$exists": True, "$ne": "assist"},
                        "state": {"$exists": True, "$ne": "user_selection"},
                        'revision': {"$exists": True, "$ne": []},
                        'line': {"$exists": True, "$ne": ""},
                        'editingLines': {"$exists": True, "$ne": []}
                        }):
        titles[pid] = f"Project {i}"
        i += 1


titles = {}
_find_titles()