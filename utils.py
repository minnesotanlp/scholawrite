import os
import subprocess
from pymongo import MongoClient
from datetime import datetime
import diff_match_patch as dmp_module
from rich.console import Console

dmp = dmp_module.diff_match_patch()

DOCUMENTS_FETCH_LIMIT = 200
HALF_FETCH_LIMIT = DOCUMENTS_FETCH_LIMIT // 2

client = MongoClient('localhost', 5001)
db = client.flask_db
collection = db.processed_data
annotation = db.annotation

console = Console()

title_to_projectId_dict = {"Shallow Synthesis of Knowledge in GPT-Generated Texts A Case Study in Automatic Related Work Composition" : "654682f220e7d557c7e67cff"}


def title_to_projectId(paperUrl):
    title = paperUrl.split("/")[-1]
    projectId = title_to_projectId_dict[title]

    return projectId


def list_projects():
    for root, subdir, files in os.walk("projects"):
        return subdir


def diff_prettyHtml(diffs):
    """
    Convert a diff array into a pretty HTML report.

    Args:
      diffs: Array of diff tuples.

    Returns:
      HTML representation.
    """
    html = []
    for each in diffs:
        op, data = each[:2]
        text = (
            data.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "&para;<br>")
        )
        if text.isspace():
            text = text.replace(" ", "&nbsp;")
        # insertion
        if op == 1:
            html.append('<ins style="background:#82E0AA;">%s</ins>' % text)
        # deletion
        elif op == -1:
            html.append('<del style="background:#F1948A;">%s</del>' % text)
        # request AI paraphrase
        elif op == 2:
            html.append('<ins style="background:#85C1E9 ;">%s</ins>' % text)
        # reject AI paraphrase suggestion
        elif op == 3:
            html.append('<ins style="background:#C39BD3;">%s</ins>' % text)
        # copy
        elif op == 4:
            html.append('<ins style="background:#FFBF00;">%s</ins>' % text)
        elif op == 0:
            html.append("<span>%s</span>" % text)
    return "".join(html)


def fetch_edits(data):
    # Form edits that will be used for visualization on client side.
    # Given a set of documents (data) retrieved from MongoDB collection
    actions = []
    revisions = []
    
    for each in data:
        timestamp = datetime.fromtimestamp(each["timestamp"] / 1000).strftime('%Y-%m-%d %H:%M:%S')

        actions.append({"username": each['username'], "timestamp": timestamp, "label": each["label"][0]})
        revisions.append({"line_nums": each["editingLines"], "diff_html": diff_prettyHtml(each["revision"])})
    return actions, revisions


def load_chunk_by_file(projectID, skip, file):
    if skip > HALF_FETCH_LIMIT:
        first_skip = skip - HALF_FETCH_LIMIT
        cur_index_in_array = HALF_FETCH_LIMIT
    else:
        first_skip = 0
        cur_index_in_array = skip

    query = {'project': projectID, "file": file}

    data = collection.find(query).sort("index", 1).skip(first_skip).limit(DOCUMENTS_FETCH_LIMIT)

    actions, revisions = fetch_edits(data)

    return {"actions": actions, "revisions": revisions, "arrayIdx": cur_index_in_array}


def run_synctex(coordinates):
    try:
        page_number = coordinates["pageNumer"]
        x = coordinates["left"]
        y = coordinates["top"]
        directory = coordinates["paperUrl"]

        command = ["synctex", "edit", "-o", f"{page_number}:{x}:{y}:main.pdf", "-d", directory]
        result = subprocess.run(command, text=True, capture_output=True)

        if result.returncode == 0:
            output_list = result.stdout.split("\n")
            file = output_list[3].split("/")[-1]

            return file

        else:
            console.log(result.stderr)
            return None
    
    except:
        console.log(result.stderr)
        return None


def get_meta_data(coordinates):
    file = run_synctex(coordinates)
    projectId = title_to_projectId(coordinates["paperUrl"])

    query = {'project': projectId, "file": file}
    no_of_doc = collection.count_documents(query)

    return {"file": file, "no_of_doc": no_of_doc}