from .utils import *
import plotly.graph_objects as go

document = annotation.find_one({"annotatorEmail": "update"})
document.pop("_id")
document.pop("annotatorEmail")

project_names = {}

label_colors = {"Idea Generation" : "rgba(86,235,211, 0.8)", "Idea Organization": "rgba(166,0,62, 0.8)", "Section Planning":"rgba(100,224,88, 0.8)",
                "Text Production" : "rgba(135,17,172, 0.8)", "Object Insertion" : "rgba(69,149,33, 0.8)", "Citation Integration":"rgba(121,193,239, 0.8)",
                "Cross-reference": "rgba(14,80,62, 0.8)", "Macro Insertion": "rgba(189,226,103, 0.8)", "Fluency" : "rgba(100,66,139, 0.8)", 
                "Coherence" : "rgba(239,161,204, 0.8)", "Clarity": "rgba(22,125,187, 0.8)", "Scientific Accuracy": "rgba(216,94,225, 0.8)", 
                "Structural": "rgba(252,209,7, 0.8)", "Textual Style": "rgba(136,60,16, 0.8)", "Visual Style": "rgba(254,183,134, 0.8)"}

project_ids = []


def labels_to_colors(labels):
    color_list = []
    for each in labels:
        color_list.append(label_colors[each])
    
    return color_list


def get_annotation_document(project):
    
    project_ids.append(project)

    project_data = {"node":{}, "link":{}}
    labels = []
    labels_dict = {}

    for sublist in document[project]["filledArray"]:
        for item in sublist:
            if item != "Artifact" and item != "No Label":
                if item in labels_dict:
                    labels_dict[item] += 1
                else:
                    labels_dict[item] = 1
                labels.append(item)

    project_data["node"]["label"] = list(labels_dict.keys())
    project_data["node"]["color"] = labels_to_colors(labels_dict)

    merged_labels = []
    max = len(labels) - 1
    for idx, label in enumerate(labels[:-1]):
        if idx + 1 == max - 1:
            merged_labels.append(label)
            break
        elif label != labels[idx+1]:
            merged_labels.append(label)

    if labels[-1] != merged_labels[-1]:
        merged_labels.append(labels[-1])

    label_count = {}
    for idx, each in enumerate(project_data["node"]["label"]):
        label_count[idx] = {}
        for jdx, label in enumerate(merged_labels[:-1]):
            if label == each:
                next_label = project_data["node"]["label"].index(merged_labels[jdx+1])
                if next_label in label_count[idx].keys():
                    label_count[idx][next_label] += 1
                else:
                    label_count[idx][next_label] = 1
    
    source = []
    target = []
    value = []
    for source_label in label_count:
        for target_label in label_count[source_label]:
            source.append(source_label)
            target.append(target_label)
            value.append(label_count[source_label][target_label])
    project_data["link"]["source"] = source
    project_data["link"]["target"] = target
    project_data["link"]["value"] = value

    return project_data


def generate_link_color(ignore_list, source, target, node_color):
    opacity = 0.4
    link_color = []

    for i in range(len(source)):
        if (source[i] in ignore_list) and (target[i] in ignore_list):
            link_color.append("rgba(0,0,0,0)")
        else:
            link_color.append(node_color[source[i]].replace("0.8", str(opacity)))
    
    return link_color


def delete_hidden_link_operation(ignore_list, source, target):
    for i in range(len(source)-1, -1, -1):
        if (source[i] in ignore_list) and (target[i] in ignore_list):
            source.pop(i)
            target.pop(i)
    

def plot_sankey_diagram(show_hidden_link, ignore_list, data):

    if not show_hidden_link:
        delete_hidden_link_operation(ignore_list, data['link']['source'], data['link']['target'])

    data['link']['color'] = generate_link_color(ignore_list, data['link']['source'], data['link']['target'], data['node']['color'])

    fig = go.Figure(data=[go.Sankey(
        # Define nodes
        node = dict(
        pad = 15,
        thickness = 15,
        line = dict(color = "black", width = 0.5),
        label =  data['node']['label'],
        color =  data['node']['color']
        ),
        # Add links
        link = dict(
        source =  data['link']['source'],
        target =  data['link']['target'],
        value =  data['link']['value'],
        color =  data['link']['color']
    ))])

    fig.update_layout(
        font_size=10,
        margin_b=150,
        margin_l = 0,
        margin_r = 0,
        margin_t = 80,
    )

    return fig
