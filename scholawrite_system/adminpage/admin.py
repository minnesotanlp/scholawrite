from modules.utils import *
from modules.overview_data import fetch_edits_by_week, fetch_edits_by_month, fetch_edits_by_year
from modules.project_data import distinct_projects, project_edits_by_week, project_edits_by_month, project_edits_by_year
from modules.user_data import distinct_usernames, user_edits_by_week, user_edits_by_month, user_edits_by_year
from modules.plot import *
from modules.sankey import get_annotation_document, plot_sankey_diagram, project_names
from modules.visual import *

import plotly.utils
import json

app = Flask(__name__)

app.secret_key = 'qearvgb12345413pibergefwva'


def get_default_date():
    latest_time_doc = collection.find({}).sort({"timestamp": -1}).limit(1)
    earliest_time_doc = collection.find({}).sort({"timestamp": 1}).limit(1)

    latest_timestamp = (latest_time_doc[0]["timestamp"]) / 1000
    earliest_timestamp = (earliest_time_doc[0]["timestamp"]) / 1000

    latest_object = datetime.utcfromtimestamp(latest_timestamp)
    earliest_object = datetime.utcfromtimestamp(earliest_timestamp)

    latest_string_list = [latest_object.year, f"{latest_object.month:02d}", f"{latest_object.isocalendar()[1]:02d}"]
    earliest_string_list = [earliest_object.year, f"{earliest_object.month:02d}", f"{earliest_object.isocalendar()[1]:02d}"]

    data = {"maxweek": f"{latest_string_list[0]}-W{latest_string_list[2]}",
            "maxmonth": f"{latest_string_list[0]}-{latest_string_list[1]}",
            "minweek": f"{earliest_string_list[0]}-W{earliest_string_list[2]}", 
            "minmonth": f"{earliest_string_list[0]}-{earliest_string_list[1]}",}

    return data


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.root_path,
                               'static/images/favicon.ico',
                               mimetype='image/vnd.microsoft.icon')


@app.route('/', methods=['GET'])
@app.route('/main', methods=['GET'])
def index():
    data = get_default_date()
    data['overview_json'] = session.get('overview_json')
    data['top_projects_json'] = session.get('top_projects_json')
    data['top_users_json'] = session.get('top_users_json')

    return render_template('main.html', **data)


@app.route('/api/main', methods=['POST'])
def process_form():
    console.log(request.form)
    key, value = next(request.form.items())
    if key == "weekly":
        result = fetch_edits_by_week(value)
    elif key == "monthly":
        result = fetch_edits_by_month(value)
    elif key == "annually":
        result = fetch_edits_by_year(value)

    overview_data = plot_stack_chart(result['edits_each_date'])
    top_projects_data = plot_stack_chart(result['top_n_projects'])
    top_users_data = plot_stack_chart(result['top_n_users'])
    overview_json = json.dumps(overview_data)
    top_projects_json = json.dumps(top_projects_data)
    top_users_json = json.dumps(top_users_data)
    session['overview_json'] = overview_json
    session['top_projects_json'] = top_projects_json
    session['top_users_json'] = top_users_json

    return redirect('/main')


@app.route('/progress', methods=['GET'])
def progress():
    # data = get_default_date()
    # data["all_pids"] = titles
    # data['project_json'] = session.get('project_json')
    # data['contributors_json'] = session.get('contributors_json')
    # return render_template('progress.html', **data)
    return render_template('progress.html')


@app.route('/project', methods=['GET'])
def project():
    data = get_default_date()
    data["all_pids"] = titles
    data['project_json'] = session.get('project_json')
    data['contributors_json'] = session.get('contributors_json')
    if "project_id" not in session:
        session["project_id"] = next(iter(titles))
    data['project_id'] = session["project_id"]
    return render_template('project.html', **data)


@app.route('/api/project', methods=['POST'])
def process_project_form():
    console.log(request.form)
    interval = request.form["interval"]
    pid = request.form["projectid"]
    session["project_id"] = pid
    if interval == "weekly":
        date = request.form["week"]
        result = project_edits_by_week(date, pid)
    elif interval == "monthly":
        date = request.form["month"]
        result = project_edits_by_month(date, pid)
    elif interval == "annually":
        date = request.form["year"]
        result = project_edits_by_year(date, pid)

    one_project_data = plot_stack_chart(result['edits_each_date'])
    contributors_data = plot_chart(result['users'])
    project_json = json.dumps(one_project_data)
    contributors_json = json.dumps(contributors_data)
    session['project_json'] = project_json
    session['contributors_json'] = contributors_json

    return redirect('/project')


@app.route('/user', methods=['GET'])
def user():
    all_uids = distinct_usernames()
    data = get_default_date()
    data["all_uids"] = all_uids
    data['user_json'] = session.get('user_json')
    data['contributions_json'] = session.get('contributions_json')
    return render_template('user.html', **data)


@app.route('/api/user', methods=['POST'])
def process_user_form():
    console.log(request.form)
    interval = request.form["interval"]
    uid = request.form["userid"]
    if interval == "weekly":
        date = request.form["week"]
        result = user_edits_by_week(date, uid)
    elif interval == "monthly":
        date = request.form["month"]
        result = user_edits_by_month(date, uid)
    elif interval == "annually":
        date = request.form["year"]
        result = user_edits_by_year(date, uid)

    one_user_data = plot_stack_chart(result['edits_each_date'])
    contributions_data = plot_chart(result['projects'])
    user_json = json.dumps(one_user_data)
    contributions_json = json.dumps(contributions_data)
    session['user_json'] = user_json
    session['contributions_json'] = contributions_json
    return redirect('/user')

@app.route('/update-sankey', methods=["POST"])
def update_sankey():
    data = request.json

    sankey_diagram_data = get_annotation_document(data.get("project_id"))
    fig = plot_sankey_diagram(data.get("show_hidden_link"), data.get("ignore_list"), sankey_diagram_data)

    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    return jsonify(graphJSON)


@app.route('/sankey/<path:project_id>')
def render_sankey(project_id):
   ignore_list = []

   sankey_diagram_data = get_annotation_document(project_id)
   fig = plot_sankey_diagram(True, ignore_list, sankey_diagram_data)
   graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

   data = {"all_pids" : project_names, "all_labels": enumerate(sankey_diagram_data['node']['label']), "graphJSON": graphJSON, "project_id": project_id}

   return render_template('sankey.html', **data)


@app.route('/sankey')
def home():
   all_labels = []
   
   data = {"all_pids" : project_names, "all_labels": enumerate(all_labels)}
   return render_template('sankey_blank.html', **data)


@app.route("/<path:filename>", methods=['GET'])
def web_static(filename):
    # if the filename has pattern "images/xxx" or no backslash "xxx"
    if re.match("^(images\/[^\/]+|[^\/]+)$", filename):
        return send_from_directory("./pdf.js-4.3.136/web/", filename)
    else:
        return send_from_directory("./pdf.js-4.3.136/", filename)


@app.route("/visual", methods=['GET'])
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
    app.run(debug=True, port=3475)