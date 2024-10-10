import os
import diff_match_patch as dmp_module
dmp = dmp_module.diff_match_patch()
dmp.Diff_Timeout = 0

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
        # no change
        elif op == 0:
            html.append("<span>%s</span>" % text)

    return "".join(html)


def get_all_text(folder_path):
   # List all files in the folder, filter only the ones starting with 'response'
    files = [f for f in os.listdir(folder_path) if f.startswith('response') and f.endswith('.txt')]

    # Sort files by their names (numerical order)
    files.sort(key=lambda x: int(x.replace('response', '').replace('.txt', '')))

    with open("../seed.txt") as file:
        seed = file.read()

    content_list = [seed]

    for file_name in files:
        file_path = os.path.join(folder_path, file_name)
        with open(file_path, 'r') as file:
            content = file.read()
            content_list.append(content)
    return content_list


def generate_html(all_text):
    all_html = []
    for i in range(len(all_text)-1):
        diff_array = dmp.diff_main(all_text[i], all_text[i+1])
        diff_html = diff_prettyHtml(diff_array)
        all_html.append({"revision":diff_html})

    return all_html



from flask import Flask, render_template, redirect, send_from_directory
from flask import request, session, jsonify
app = Flask(__name__)

@app.route('/', methods=['GET'])
@app.route('/main', methods=['GET'])
def index():
    all_text = get_all_text("../second_attempt/iterative_responses")
    all_html = generate_html(all_text)
    return render_template('main.html', all_html=all_html, all_html_len=len(all_html))