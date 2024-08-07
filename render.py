import re

from flask import Flask, render_template, send_from_directory, request, jsonify
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


@app.route("/api/section", methods=["POST"])
def send_metadata():
    post_data = request.get_json(force=True)
    meta_data = get_meta_data(post_data["filename"], post_data["paperUrl"])
    return jsonify(meta_data)


@app.route("/api/paragraph", methods=["POST"])
def construct_map():
    post_data = request.get_json(force=True)

    paperUrl = post_data["paperUrl"]
    pageNumber = str(post_data["pageNumber"])
    coordinates = post_data["coordinates"]

    paragraph_layout, paragraph_data, pdf_to_paragraph = load_from_disk(paperUrl)

    temp_pdf_to_paragraph = {pageNumber:[]}

    for coordinate in coordinates:

        temp_pdf_to_paragraph[pageNumber].append(get_one_paragraph_loc(coordinate))
    
    pdf_to_paragraph.update(temp_pdf_to_paragraph)

    save_to_disk(paperUrl, [paragraph_layout, paragraph_data, pdf_to_paragraph])

    return jsonify(pdf_to_paragraph)


@app.route("/api/mapping", methods=["POST"])
def send_map():
    post_data = request.get_json(force=True)
    paper_url = post_data["paperUrl"]

    ret_data = {}

    if os.path.exists(paper_url+"/main.synctex.gz"):
        ret_data["isavailable"] = True
        combined_data = load_from_disk(paper_url)
        ret_data.update(combined_data[2])
    else:
        ret_data["isavailable"] = False
    
    return jsonify(ret_data)


@app.route('/api/monitor', methods=['POST'])
def get_500_edit():
    info = request.get_json(force=True)

    console.log(info)

    projectId = title_to_projectId(info["paperUrl"])

    data = load_chunk_by_file(projectId, info["idx"], info["file"])

    return jsonify(data)


if __name__ == '__main__':
    app.run(debug=True, port=8845)