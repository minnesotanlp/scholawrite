import os
from pymongo import MongoClient
from datetime import datetime
import diff_match_patch as dmp_module
from rich.console import Console

dmp = dmp_module.diff_match_patch()

DOCUMENTS_FETCH_LIMIT = 200
HALF_FETCH_LIMIT = DOCUMENTS_FETCH_LIMIT // 2

client = MongoClient('localhost', 6000)
db = client.flask_db
collection = db.processed_data
annotation = db.annotation

console = Console()


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

        actions.append({"file": each["file"], "username": each['username'], "timestamp": timestamp})
        revisions.append({"line_nums": each["editingLines"], "diff_html": diff_prettyHtml(each["revision"])})
    return actions, revisions, len(actions)


def load_chunk_by_file(projectID, skip, file):
    if skip > HALF_FETCH_LIMIT:
        first_skip = skip - HALF_FETCH_LIMIT
    else:
        first_skip = 0

    query = {'project': projectID, "file": file}

    data = collection.find(query).sort("index", 1).skip(first_skip).limit(DOCUMENTS_FETCH_LIMIT)

    actions, revisions, edits_length = fetch_edits(data)

    return {"actions": actions, "revisions": revisions, "arrayIdx": HALF_FETCH_LIMIT}