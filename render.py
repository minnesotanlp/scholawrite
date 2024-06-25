import re

from flask import Flask, render_template, send_from_directory
from utils import *

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
    data = {}
    data["project_names"] = list_projects()
    return render_template('viewer.html', **data)


@app.route("/projects/<path:project_name>", methods = ['GET'])
def find_file_name(project_name):
    return send_from_directory(f"./projects/{project_name}", "main.pdf")



if __name__ == '__main__':
    app.run(debug=True)