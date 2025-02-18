import os
import re
import diff_match_patch as dmp_module
dmp = dmp_module.diff_match_patch()
dmp.Diff_Timeout = 0

from dotenv import load_dotenv
load_dotenv()

from tqdm import tqdm

abs_path = os.getenv("PATH_TO_WRITING")
abs_seeds_path = os.getenv("PATH_TO_SEEDS")

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


def clean_text(text):
    text = re.sub(r"<del>.*?<\/del>", "", text, flags=re.DOTALL)

    text = re.sub(r"<same>(.*?)<\/same>", r"\1", text, flags=re.DOTALL)

    text = re.sub(r"<add>(.*?)<\/add>", r"\1", text, flags=re.DOTALL)

    tags_to_remove = ["<add>", "</add>", "<del>", "</del>", "<same>", "</same>"]
    for tag in tags_to_remove:
        text = text.replace(tag, "")
    
    return text


def get_all_text(folder_path, path_to_seed):
    
    files = []
    for i in range(100):
        files.append(f"iter_generation_{i}.txt")

    with open(path_to_seed+".txt") as file:
        seed = file.read()

    content_list = [seed, seed]
    for file_name in files:
        file_path = os.path.join(folder_path+"/generation/", file_name)

        with open(file_path, 'r') as file:
            content = file.read()
            content = clean_text(content)
            content_list.append(content)

    return content_list


def generate_html(all_text):
    all_html = []

    for i in tqdm(range(len(all_text)-1)):
        diff_array = dmp.diff_main(all_text[i], all_text[i+1])
        dmp.diff_cleanupSemantic(diff_array)
        diff_html = diff_prettyHtml(diff_array)

        all_html.append({"revision":diff_html})

    return all_html


def generate_label(folder_path):
    files = []
    label_list = [{"label": "Showing Seed"}]

    for i in range(100):
        files.append(f"iter_intention_{i}.txt")

    for file_name in files:
        file_path = os.path.join(folder_path+"/intention/", file_name)
        with open(file_path, 'r') as file:
            content = file.read()
            label_list.append({"label":content})

    return label_list


from flask import Flask, render_template, redirect, send_from_directory
from flask import request, session, jsonify, url_for

app = Flask(__name__)
app.secret_key="awirhbgvfiparo;arngvawrgovub"

@app.route('/api/seed', methods=['POST'])
def switch_seed():
    session['seed_doc'] = request.form.get("seed_doc")
    return redirect(url_for('index'))


@app.route('/', methods=['GET'])
@app.route('/main', methods=['GET'])
def index():
    if "seed_doc" in session:
        
        seed = session["seed_doc"]
        if seed not in all_seeds:
            seed = all_seeds[0]
            session['seed_doc'] = all_seeds[0]
        
        llama3_output = all_output[outputs[0]][seed]
        llama8_output = all_output[outputs[1]][seed]

        return render_template('main.html', llama3=llama3_output, llama8=llama8_output, seed=session['seed_doc'], all_seeds=all_seeds)
    else:
        return render_template('main.html', llama3={"all_html": [], "all_html_len": 0, "all_label": []}, llama8={"all_html": [], "all_html_len": 0, "all_label": []}, seed="", all_seeds=all_seeds)


def main():
    global outputs
    global all_seeds
    global all_output

    outputs = ["llama8_SW_output", "llama8_meta_output"]
    all_seeds = ["seed1", "seed2", "seed3", "seed4"]
    all_output = {}

    for output in outputs:
        all_output[output] = {}
        for seed in all_seeds:
            print(output, seed)
            path_to_folder = os.path.join(abs_path, output, seed)
            path_to_seed = os.path.join(abs_seeds_path, seed)

            all_label = generate_label(path_to_folder)
            all_text = get_all_text(path_to_folder, path_to_seed)
            all_html = generate_html(all_text)
        
            llama_output = {"all_html": all_html, "all_html_len": len(all_html)-1, "all_label": all_label}

            all_output[output][seed]=llama_output

    app.run(port=19198, debug=False)


if __name__ == '__main__': 
    main()
