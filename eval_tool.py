import os
import diff_match_patch as dmp_module
dmp = dmp_module.diff_match_patch()
dmp.Diff_Timeout = 0
path_to_llama_gen = "../../final_iterative_writing_results/llama_output/"
path_to_gpt = "../../final_iterative_writing_results/gpt_output/"


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
    
    files = []
    for i in range(100):
        files.append(f"iter_generation_{i}.txt")

    with open(f"{folder_path}/seed.txt") as file:
        seed = file.read()

    content_list = [seed]
    for file_name in files:
        file_path = os.path.join(folder_path+"/generation/", file_name)
        with open(file_path, 'r') as file:
            content = file.read()
            content_list.append(content)
    return content_list


def generate_html(all_text):
    all_html = []

    for i in range(len(all_text)-1):
        diff_array = dmp.diff_main(all_text[i], all_text[i+1])
        dmp.diff_cleanupSemantic(diff_array)
        diff_html = diff_prettyHtml(diff_array)

        all_html.append({"revision":diff_html})

    return all_html


def generate_label(folder_path):
    files = []
    label_list = []

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
        print(session["seed_doc"])
        if session['seed_doc'] == "Intro":
            return render_template('main.html', llama=llama_intro, gpt=gpt_intro, seed=session['seed_doc'])
        else:
            return render_template('main.html', llama=llama_title, gpt=gpt_title, seed=session['seed_doc'])
    else:
        return render_template('main.html', llama={"all_html": [], "all_html_len": 0, "all_label": []}, gpt={"all_html": [], "all_html_len": 0, "all_label": []}, seed="")


def main():
    global llama_intro, llama_title, gpt_intro, gpt_title

    path_to_folder = "../../final_iterative_writing_results/llama_output/intro"
    all_label = generate_label(path_to_folder)
    all_text = get_all_text(path_to_folder)
    all_html = generate_html(all_text)
    llama_intro = {"all_html": all_html, "all_html_len": len(all_html)-1, "all_label": all_label}

    path_to_folder = "../../final_iterative_writing_results/llama_output/title"
    all_label = generate_label(path_to_folder)
    all_text = get_all_text(path_to_folder)
    all_html = generate_html(all_text)
    llama_title = {"all_html": all_html, "all_html_len": len(all_html)-1, "all_label": all_label}

    path_to_folder = "../../final_iterative_writing_results/gpt_output/intro"
    all_label = generate_label(path_to_folder)
    all_text = get_all_text(path_to_folder)
    all_html = generate_html(all_text)
    gpt_intro = {"all_html": all_html, "all_html_len": len(all_html)-1, "all_label": all_label}

    path_to_folder = "../../final_iterative_writing_results/gpt_output/title"
    all_label = generate_label(path_to_folder)
    all_text = get_all_text(path_to_folder)
    all_html = generate_html(all_text)
    gpt_title = {"all_html": all_html, "all_html_len": len(all_html)-1, "all_label": all_label}


    app.run(port=19198, debug=True)


if __name__ == '__main__': 
    main()
