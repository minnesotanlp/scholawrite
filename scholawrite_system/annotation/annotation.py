from modules.utils import *
from modules.monitor import initialize_admin_data, initialize_file_data, initialize_user_data, load_chunk_by_time, load_chunk_by_file, load_chunk_by_user

app = Flask(__name__)

app.secret_key = 'qearvgb12345413pibergefwva'

@app.before_request
def before_request():
    project_id = request.args.get('project_id', default=None)
    if project_id is not None:
        session["project_id"] = project_id
    elif "project_id" not in session:
        session["project_id"] = next(iter(titles))


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/api/login', methods=['POST'])
def login():
    console.log(request.form['annotatorEmail'])
    session["annotatorEmail"] = request.form['annotatorEmail']
    return redirect('/monitorwhole')


@app.route('/monitorwhole', methods=['GET'])
def monitor_whole():
    if "annotatorEmail" not in session:
        return redirect("/")
    data = initialize_admin_data(session.get("project_id"))
    data["project_id"] = session["project_id"]
    data["annotatorEmail"] = session["annotatorEmail"]
    data["all_pids"] = titles
    return render_template('monitorWhole.html', **data)


@app.route('/api/monitorwhole', methods=['POST'])
def get_500_edit():
    info = request.get_json(force=True)
    data = load_chunk_by_time(session.get("project_id"), info["idx"])
    return jsonify(data)


@app.route('/monitor', methods=['GET'])
def monitor():
    if "annotatorEmail" not in session:
        return redirect("/")
    project_id = session.get("project_id")
    data = initialize_admin_data(project_id)
    data.update(initialize_file_data(project_id))
    data["project_id"] = project_id
    data["annotatorEmail"] = session["annotatorEmail"]
    data["all_pids"] = titles
    return render_template('monitor.html', **data)


@app.route('/api/monitor', methods=['POST'])
def get_500_edit_file():
    info = request.get_json(force=True)
    data = load_chunk_by_file(session.get("project_id"), info["idx"], info["file"])
    return jsonify(data)


@app.route('/monitoruser', methods=['GET'])
def user_monitor():
    if "annotatorEmail" not in session:
        return redirect("/")
    project_id = session.get("project_id")
    data = initialize_admin_data(project_id)
    data.update(initialize_user_data(project_id))
    data["project_id"] = project_id
    data["annotatorEmail"] = session["annotatorEmail"]
    data["all_pids"] = titles
    return render_template('monitorUser.html', **data)


@app.route('/api/monitoruser', methods=['POST'])
def get_500_edit_user():
    info = request.get_json(force=True)
    data = load_chunk_by_user(session.get("project_id"), info["idx"], info["file"])
    return jsonify(data)


@app.route('/api/save', methods=['POST'])
def save():
    try:
        info = request.get_json(force=True)
        new_doc = {"annotatorEmail": session["annotatorEmail"], session.get("project_id"): info}
        match = {"annotatorEmail": session["annotatorEmail"]}
        annotation.update_one(match, {"$set": new_doc}, upsert=True)
        return jsonify({"message": "success"}), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500


@app.route('/api/load', methods=['GET'])
def load():
    try:
        match = {"annotatorEmail": session["annotatorEmail"]}
        console.log(match, session["project_id"])
        data = annotation.find_one(match)
        loadData = {}
        if data is not None:
            if session["project_id"] in data:
                loadData = data[session["project_id"]]

        return jsonify(loadData), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
