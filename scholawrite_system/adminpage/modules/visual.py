import os
import subprocess
import pickle

from pymongo import MongoClient
from datetime import datetime
import diff_match_patch as dmp_module
from rich.console import Console

dmp = dmp_module.diff_match_patch()

DOCUMENTS_FETCH_LIMIT = 200
HALF_FETCH_LIMIT = DOCUMENTS_FETCH_LIMIT // 2

client = MongoClient('mongo', 27017)
db = client.flask_db
collection = db.processed_data
annotation = db.annotation

console = Console()

title_to_projectId_dict = {}

paragraph_layout = {}
paragraph_data = {}


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
        page_number = coordinates["pageNumber"]
        x = coordinates["left"]
        y = coordinates["top"]
        directory = coordinates["paperUrl"]

        command = ["synctex", "edit", "-o", f"{page_number}:{x}:{y}:main.pdf", "-d", directory]
        result = subprocess.run(command, text=True, capture_output=True)

        if result.returncode == 0:
            output_list = result.stdout.split("\n")
            file = output_list[3].split("/")[-1]
            line = output_list[4].split(":")[-1]

            return [file, line]

        else:
            console.log(result.stderr)
            return None

    except Exception as e:
        console.log(e)
        return None


def get_meta_data(file, paper_url):
    projectId = title_to_projectId(paper_url)

    query = {'project': projectId, "file": file}
    
    all_labels = []
    data = collection.find(query).sort("index", 1)
    for each in data:
        all_labels.append(each["label"][0])

    no_of_doc = collection.count_documents(query)

    return {"file":file, "no_of_doc": no_of_doc, "all_labels": all_labels}


def find_new_paragraph_range(file, line_num, folder_path):
    file_path = ""

    for (dirpath, dirnames, filenames) in os.walk(folder_path):
        if file in filenames:
            file_path = dirpath + "/" + file
    if file_path == "":
        console.log("Not valid path", file, line_num)
        return {"file": file, "begin": line_num, "end": line_num} 

    with open(file_path, "r") as fh:
        lines = fh.readlines()
        if line_num < 1 or line_num > len(lines):
            console.log("Line out of range", file, line_num)
            return {"file": file, "begin": line_num, "end": line_num}

        # Get the content above the specified line and initialize paragraph data
        content_above = ''.join(lines[:line_num - 1])
        first_half_paragraph = ""
        paragraph_begin = line_num

        # Get the content of the specified line and initialize paragraph data
        content_online = lines[line_num - 1]
        if content_online == "\n":
            console.log("Empty line", line_num, file)
            try:
                paragraph_begin, paragraph_end = paragraph_layout[file][-1]
                return {"file": file, "begin": paragraph_begin, "end": paragraph_end}
            except IndexError:
                return {"file": file, "begin": line_num, "end": line_num}
        
        # Get the content below the specified line and initialize paragraph data
        content_below = ''.join(lines[line_num:])
        second_half_paragraph = content_online
        paragraph_end = line_num

        if content_online[:11] != "\paragraph{" and content_online[:15] != "\subsubsection{" and content_online[:12] != "\subsection{":
            for char_above in content_above[::-1]:
                first_half_paragraph = char_above + first_half_paragraph
                if "\paragraph{" == first_half_paragraph[:11]:
                    break
                if "\subsubsection{" == first_half_paragraph[:15]:
                    break
                if "\subsection{" == first_half_paragraph[:12]:
                    break
                if "\n\n" == first_half_paragraph[:2]:
                    first_half_paragraph = first_half_paragraph[2:]
                    paragraph_begin += 1
                    break
                if char_above == "\n":
                    paragraph_begin -= 1
        

        for char_below in content_below:
            second_half_paragraph = second_half_paragraph + char_below
            if char_below == "\n":
                paragraph_end += 1
            if "\paragraph{" == second_half_paragraph[-11:]:
                second_half_paragraph = second_half_paragraph[:-11]
                if second_half_paragraph[-1] == "\n":
                    second_half_paragraph = second_half_paragraph[:-1]
                    paragraph_end -= 1
                break
            if "\subsubsection{" == second_half_paragraph[-15:]:
                second_half_paragraph = second_half_paragraph[:-15]
                if second_half_paragraph[-1] == "\n":
                    second_half_paragraph = second_half_paragraph[:-1]
                    paragraph_end -= 1
                break
            if "\subsection{" == second_half_paragraph[-12:]:
                second_half_paragraph = second_half_paragraph[:-12]
                if second_half_paragraph[-1] == "\n":
                    second_half_paragraph = second_half_paragraph[:-1]
                    paragraph_end -= 1
                break
            if "\n\n" == second_half_paragraph[-2:]:
                second_half_paragraph = second_half_paragraph[:-1]
                paragraph_end -= 1
                break

        paragraph_layout[file].append((paragraph_begin, paragraph_end))
        paragraph_data[file + ":" + str(paragraph_begin) + ":" + str(
            paragraph_end)] = first_half_paragraph + second_half_paragraph

        return {"file": file, "begin": paragraph_begin, "end": paragraph_end}


def save_to_disk(path_to_folder, combined_data):
    with open(path_to_folder + '/paragraph.pkl', 'wb') as file:
        pickle.dump(combined_data, file)


def load_from_disk(path_to_folder):
    try:
        with open(path_to_folder + '/paragraph.pkl', 'rb') as file:
            combined_data = pickle.load(file)
    except FileNotFoundError:
        combined_data = [{}, {}, {}]
        
    return combined_data


def get_one_paragraph_loc(coordinates):
    
    result = run_synctex(coordinates)

    if result:
        file = result[0]
        line = int(result[1])

        if file in paragraph_layout:
            paragraph_ranges = paragraph_layout[file]
            for begin, end in paragraph_ranges:
                if begin <= line <= end:
                    return {"file": file, "begin": begin, "end": end}
        else:
            paragraph_layout[file] = []
            
        file_begin_end = find_new_paragraph_range(file, line, coordinates["paperUrl"])
        return file_begin_end

