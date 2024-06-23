import re

from flask import Flask, render_template, send_from_directory
# from pymongo import MongoClient

# client = MongoClient('localhost', 6000)
# db = client.flask_db
# collection = db.processed_data

from rich.console import Console
console = Console()

app = Flask(__name__, template_folder="./pdf.js-4.3.136/web")


@app.route("/<path:filename>", methods=['GET'])
def web_static(filename):
    # if the filename has pattern "images/xxx" or no backslash "xxx"
    if re.match("^(images\/[^\/]+|[^\/]+)$", filename):
        return send_from_directory("./pdf.js-4.3.136/web/", filename)
    else:
        return send_from_directory("./pdf.js-4.3.136/", filename)


@app.route("/", methods=['GET'])
def render_main_page():
    return render_template('viewer.html')


if __name__ == '__main__':
    app.run(debug=True)