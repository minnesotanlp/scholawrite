# from .post_process import process_copy_and_paraphrase
import diff_match_patch as dmp_module
from .utils import *
import sys

dmp = dmp_module.diff_match_patch()
CRUMBLED_THRESHOLD = 6
DOCUMENTS_FETCH_LIMIT = 200
HALF_FETCH_LIMIT = DOCUMENTS_FETCH_LIMIT // 2


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


def initialize_admin_data(projectID):
    # Uncomment this line if you want to do data cleaning: process_copy_and_paraphrase()
    # this section is to get the frame from the first 500 edits
    query = {'project': projectID}

    data = collection.find(query).sort("index", 1).skip(0).limit(DOCUMENTS_FETCH_LIMIT)

    actions, revisions, edits_length = fetch_edits(data)

    # this section is to get the total number of document
    no_of_doc = collection.count_documents(query)

    # this section is to get the name of each file in this project
    filenames = collection.distinct("file", query)

    # "actions" contains filename, username, and time for each frame
    # "revisions" contains line number and difference HTML(HTML for text reconstruction)
    return {"no_of_doc": no_of_doc, "filenames": filenames, "actions": actions, "revisions": revisions,}


def initialize_file_data(projectID):
    query = {'project': projectID}

    # this section is for retrieve the global index for each file
    cursor = collection.find(query).sort("index", 1)
    filenames = collection.distinct("file", query)

    # initialize dictionary use to map global(project-level) index to local(file-level) index
    global_indexes = {filenames[i]: [] for i in range(len(filenames))}
    index = 0

    # loop through document in one project to map each edit to each file
    for document in cursor:
        global_indexes[document["file"]].append(index)
        index += 1

    no_of_doc_file = {key: len(value) for key, value in global_indexes.items()}

    return {"no_of_doc_file": no_of_doc_file, "global_indexes": global_indexes}


def initialize_user_data(projectID):
    query = {'project': projectID}

    # this section is for retrieve the global index for each username
    cursor = collection.find(query).sort("index", 1)
    usernames = collection.distinct("username", query)

    # initialize dictionary use to map global(project-level) index to local(user-level) index
    user_indexes = {usernames[i]: [] for i in range(len(usernames))}
    index = 0

    # loop through document in one project to map each edit to each file
    for document in cursor:
        user_indexes[document["username"]].append(index)
        index += 1

    no_of_doc_user = {key: len(value) for key, value in user_indexes.items()}

    return {"usernames": usernames, "no_of_doc_user": no_of_doc_user, "user_indexes": user_indexes}


def load_chunk_by_time(projectID, skip):
    if skip > HALF_FETCH_LIMIT:
        first_skip = skip - HALF_FETCH_LIMIT
    else:
        first_skip = 0

    query = {'project': projectID}

    data = collection.find(query).sort("index", 1).skip(first_skip).limit(DOCUMENTS_FETCH_LIMIT)

    actions, revisions, edits_length = fetch_edits(data)

    return {"actions": actions, "revisions": revisions, "arrayIdx": HALF_FETCH_LIMIT}


def load_chunk_by_file(projectID, skip, file):
    if skip > HALF_FETCH_LIMIT:
        first_skip = skip - HALF_FETCH_LIMIT
        arrayIdx = HALF_FETCH_LIMIT
    else:
        first_skip = 0
        arrayIdx = 0

    query = {'project': projectID, "file": file}

    data = collection.find(query).sort("index", 1).skip(first_skip).limit(DOCUMENTS_FETCH_LIMIT)

    actions, revisions, edits_length = fetch_edits(data)

    return {"actions": actions, "revisions": revisions, "arrayIdx": arrayIdx}


def load_chunk_by_user(projectID, skip, username):
    if skip > HALF_FETCH_LIMIT:
        first_skip = skip - HALF_FETCH_LIMIT
        arrayIdx = HALF_FETCH_LIMIT
    else:
        first_skip = 0
        arrayIdx = 0

    query = {'project': projectID, "username": username}

    data = collection.find(query).sort("index", 1).skip(first_skip).limit(DOCUMENTS_FETCH_LIMIT)

    actions, revisions, edits_length = fetch_edits(data)

    return {"actions": actions, "revisions": revisions, "arrayIdx": arrayIdx}