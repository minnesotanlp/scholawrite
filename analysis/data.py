import sys
import math
import random 
from collections import Counter

import numpy as np
import scipy
from scipy import stats
import pandas as pd
import holoviews as hv
from holoviews import opts, dim
from bokeh.io import show, export_svgs
from bokeh.models.annotations import LabelSet
import plotly.graph_objects as go
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import dictances
import svglib.svglib as svglib
from reportlab.graphics import renderPDF

#hv.extension('bokeh')
hv.extension('matplotlib')
hv.output(size=200)

from dataset import KeystrokeDataset
from diff_utils import get_word_diff, count_op
from plotting import gantt_chart, plot_distributions
from taxonomy import Taxonomy

annotator_email = "update"

d = KeystrokeDataset()

def visualize_labels(project_id):
  annotation_df = d.get_annotations(annotator_email)

  #categories = ("Planning", "Implementation", "Revision")

  colors = [Taxonomy["Planning"]["Color"], Taxonomy["Implementation"]["Color"], Taxonomy["Revision"]["Color"]]

  spans = annotation_df[project_id][0]["filledArray"]
  spans = [x[0] for x in spans]
  
  label_counts = Counter(spans)
  sorted_data = label_counts.most_common()
  print(sorted_data)

  categories = [item[0] for item in sorted_data]
  counts = [item[1] for item in sorted_data]

  def get_color(lab):
    if lab in Taxonomy["Planning"]["Classes"]:
      return Taxonomy["Planning"]["Color"]
    elif lab in Taxonomy["Implementation"]["Classes"]:
      return Taxonomy["Implementation"]["Color"]
    elif lab in Taxonomy["Revision"]["Classes"]:
      return Taxonomy["Revision"]["Color"]
    else:
      return 'red'

  colors = [get_color(x) for x in categories]

  print(counts)

  plt.bar(categories, counts, color=colors)
  plt.xlabel('Label')
  plt.ylabel('Count')
  plt.title('Writing Intetion Frequency')
  plt.xticks(rotation=45, ha='right')
  plt.tight_layout()
  plt.savefig(f"labels_{project_id}.png")

def writing_activities_broad(project_id):
  annotation_df = d.get_annotations(annotator_email)

  categories = ("Planning", "Implementation", "Revision")

  colors = [Taxonomy["Planning"]["Color"], Taxonomy["Implementation"]["Color"], Taxonomy["Revision"]["Color"]]

  spans = annotation_df[project_id][0]["filledArray"]
  spans = [x[0] for x in spans]

  new_spans = []

  for span in spans:
    if (span in Taxonomy["Planning"]["Classes"]):
      new_spans.append("Planning")
    elif (span in Taxonomy["Implementation"]["Classes"]):
      new_spans.append("Implementation")
    elif (span in Taxonomy["Revision"]["Classes"]):
      new_spans.append("Revision")
    else:
      print("should not happen: ", span)
  
  spans = new_spans

  n_spans = len(spans)

  start_times = np.arange(n_spans)
  durations = np.ones(n_spans)
  
  gantt_chart(spans, durations, start_times, categories, colors=colors, rounded=True, save=True, filepath=f"/Users/rvolkov/Documents/projects/nlp_research/analysis_temp/figures/writing_activities_{project_id}_broad.pdf")

def writing_activities_detailed(project_id):
  annotation_df = d.get_annotations(annotator_email)

  categories = Taxonomy["Planning"]["Classes"] + Taxonomy["Implementation"]["Classes"] + Taxonomy["Revision"]["Classes"]

  colors = [Taxonomy["Planning"]["Color"]] * len(Taxonomy["Planning"]["Classes"])
  colors += [Taxonomy["Implementation"]["Color"]] * len(Taxonomy["Implementation"]["Classes"])
  colors += [Taxonomy["Revision"]["Color"]] * len(Taxonomy["Revision"]["Classes"])

  spans = annotation_df[project_id][0]["filledArray"]
  spans = [x[0] for x in spans]
  spans = [x for x in spans if x in categories]

  n_spans = len(spans)

  start_times = np.arange(n_spans)
  durations = np.ones(n_spans)
  
  gantt_chart(spans, durations, start_times, categories, colors=colors, rounded=True, save=True, filepath=f"/Users/rvolkov/Documents/projects/nlp_research/analysis_temp/figures/writing_activities_{project_id}_no_artifact.pdf")

def get_writing_activities_occurances(project_id):
  annotation_df = d.get_annotations(annotator_email)
  annotations = annotation_df[project_id][0]["filledArray"]

  annotations = [x[0] for x in annotations]

  counts = {}

  for a in annotations:
    if (a in counts):
      counts[a] += 1
    else:
      counts[a] = 1
  
  #print(project_id, counts)
  return counts

#for project_id in project_ids:
#  writing_activities_broad(project_id)
#  writing_activities_detailed(project_id)

def do_word_diff_new(project_id):
  activity_df = d.get_activity(project_id)
  #activity_df["word diff"] = activity_df["revision"].apply(get_word_diff)

  pivot_df = pd.pivot_table(activity_df, values="edits", index="timestamp", columns="file", aggfunc="size", fill_value=0)

  print(pivot_df.head())

def do_word_diff(project_id):
  activity_df = d.get_visual_data(project_id)
  activity_df["word diff"] = activity_df["revision"].apply(get_word_diff)

  arr = activity_df["word diff"].to_numpy()

  words_added = 0
  words_deleted = 0

  for i in range(arr.shape[0]):
    if (arr[i] > 0):
      words_added += arr[i]
    elif (arr[i] < 0):
      words_deleted -= arr[i]
    
  out = {
    "words added": words_added,
    "words deleted": words_deleted,
    "recorded actions": len(arr)
  }

  return out

  # run script to show that there are other labels?

#for project_id in project_ids:
#  print("project_id: ", project_id)
#  do_word_diff(project_id)
#  print(" ")

def get_file_interconnectedness_score(project_id):
  def check_file(df):
    if (df["file"] == df["next_file"]):
        return None
    else:
        return df["next_file"]
  
  df = d.get_visual_data(project_id)

  df["next_file"] = df["file"].shift(1)
  df["next_file"] = df.apply(check_file, axis = 1)

  relevant_files = [col for col in df["next_file"].unique() if (col != None and col != "null") and ('.tex' in col or '.bib' in col)]

  df = df[df["file"].isin(relevant_files) & df["next_file"].isin(relevant_files)]
  df = df[["next_file", "file"]]

  edges_df = df.groupby(['file', 'next_file']).size().reset_index(name='value')
  edges_df = edges_df.rename(columns={"file": "source", "next_file": "target"})

  edges_df["total"] = edges_df.groupby(["source"])["value"].transform('sum')
  edges_df["probability"] = edges_df.apply(lambda x: x["value"] / x["total"], axis=1)

  print(edges_df.head(100))

  #df_max = edges_df.groupby("source", as_index=False).max()
  indices = edges_df.groupby('source')['value'].idxmax()

  df_max = edges_df.loc[indices].reset_index(drop=True)

  print(df_max.head(100))

  df_max["reflexive"] = df_max.apply(lambda x: (x["source"] == df_max.loc[df_max["source"] == x["target"]]["target"].item()), axis=1)

  print(df_max.to_latex(columns=["source", "target", "probability", "reflexive"], index=False, float_format="%.2f"))

def get_col_interconnectedness_score(project_id, col_name, project_idx, color_map):
  next_col_name = f"next_{col_name}"

  def check_file(df):
    nonlocal col_name, next_col_name
    if (df[col_name] == df[next_col_name]):
        return None
    else:
        return df[next_col_name]
  
  df = d.get_visual_data(project_id)

  df["label"] = df["label"].apply(lambda x: x[0])

  def get_higher_level_intention(intention):
    if (intention in Taxonomy["Planning"]["Classes"]):
      return "Planning"
    elif (intention in Taxonomy["Implementation"]["Classes"]):
      return "Implementation"
    elif (intention in Taxonomy["Revision"]["Classes"]):
      return "Revision"
    else:
      return "None"
    
  df["label"] = df["label"].apply(lambda x: get_higher_level_intention(x))

  df[next_col_name] = df[col_name].shift(1)
  df[next_col_name] = df.apply(check_file, axis = 1)

  #relevant_files = [col for col in df[next_col_name].unique() if (col != None and col != "null") and ('.tex' in col or '.bib' in col)]
  relevant_labels = [col for col in df[next_col_name].unique() if (col != None and col != "null") and (col not in ("Artifact", "No Label", "None"))]

  df = df[df[col_name].isin(relevant_labels) & df[next_col_name].isin(relevant_labels)]
  df = df[[next_col_name, col_name]]

  edges_df = df.groupby([col_name, next_col_name]).size().reset_index(name='value')
  #edges_df = edges_df.rename(columns={"file": "source", "next_file": "target"})

  edges_df["total"] = edges_df.groupby([col_name])["value"].transform('sum')
  edges_df["probability"] = edges_df.apply(lambda x: x["value"] / x["total"], axis=1)

  #print(edges_df.head(100))

  #df_max = edges_df.groupby("source", as_index=False).max()
  indices = edges_df.groupby(col_name)['value'].idxmax()

  df_max = edges_df.loc[indices].reset_index(drop=True)

  #print(df_max.head(100))

  df_max["reflexive"] = df_max.apply(lambda x: (x[col_name] == df_max.loc[df_max[col_name] == x[next_col_name]][next_col_name].item()), axis=1)

  latex_table = df_max.to_latex(columns=[col_name, next_col_name, "probability", "reflexive"], index=False, float_format="%.2f")

  f = open(f"{col_name}_latex_table.txt", "w")
  f.write(latex_table)
  f.close()

  # make plot
  edges_df = df.groupby([col_name, next_col_name]).size().reset_index(name='value')
  edges_df = edges_df.rename(columns={col_name: "source", next_col_name: "target"})

  edges_df['color'] = edges_df['source'].map(color_map)

  nodes = set(edges_df["source"].unique().tolist())
  nodes_B = set(edges_df["target"].unique().tolist())
  nodes = list(nodes.union(nodes_B))
  #node_colors = [color_map[x] for x in node_s]

  nodes = sorted(nodes)

  nodes_df = pd.DataFrame(nodes, columns=["label"])
  nodes_df["node_colors"] = nodes_df["label"].apply(lambda x: color_map[x])

  edges_df["source"] = edges_df["source"].apply(lambda x: nodes.index(x))
  edges_df["target"] = edges_df["target"].apply(lambda x: nodes.index(x))

  hv_nodes = hv.Dataset(nodes_df, 'index')

  chord = hv.Chord((edges_df, hv_nodes))
  chord.opts(
    opts.Chord(
               edge_color='color',
               node_color='node_colors',
               #labels='label',
               #hooks=[rotate_label]
               #backend_opts={
               #  "labels.set_rotation": 0,
               #  "labels.horizontalalignment": 'left',
               #  }
               ))

  label_data = chord.nodes.data.drop(['index'], axis=1)
  label_data['rotation'] = np.arctan((label_data.y / label_data.x))
  label_data['y'] = label_data['y'].apply(lambda x: x * 1.5)
  label_data['x'] = label_data['x'].apply(lambda x: x * 1.5)

  print(label_data.columns)

  labels = hv.Labels(label_data)
  labels.opts(
    opts.Labels(
      padding=0.12, rotation=dim('rotation')*1260/22, color=dim('node_colors').str()))

  chord = chord * labels

  chord

  #show(hv.render(chord))  # Explicitly show the plot

  #print(f'{col_name}_flow.pdf')

  # Render the plot
  #plot = hv.output(chord, backend='matplotlib')

  # Get the current axes
  #ax = plt.gca()

  # Rotate the node labels manually
  #for label in ax.texts:
      #label.set_rotation(45)  # Rotate the labels by 45 degrees

  #plt.show()

  hv.save(chord, filename=f"{col_name}_flow_project_{project_idx}.pdf", fmt='pdf')

#print("Plot saved as PDF.")

def color_node_map(classes):
  cmap = plt.get_cmap('tab20')
  num_classes = len(classes)
  
  colors = [cmap(i % 20) for i in range(num_classes)]
  hex_colors = [matplotlib.colors.rgb2hex(color) for color in colors]
  
  return dict(zip(classes, hex_colors))

def get_file_edits(project_id):
  def check_file(df):
    if (df["file"] == df["next_file"]):
        return None
    else:
        return df["next_file"]
  
  df = d.get_visual_data(project_id)

  df["next_file"] = df["file"].shift(1)
  df["next_file"] = df.apply(check_file, axis = 1)

  relevant_files = [col for col in df["next_file"].unique() if (col != None and col != "null") and ('.tex' in col or '.bib' in col)]

  df = df[df["file"].isin(relevant_files) & df["next_file"].isin(relevant_files)]
  df = df[["next_file", "file"]]

  edges_df = df.groupby(['file', 'next_file']).size().reset_index(name='value')
  edges_df = edges_df.rename(columns={"file": "source", "next_file": "target"})

  print(edges_df.head(100))

  def rotate_labels(plot, element):
      graph = plot.handles['graph']
      for label in graph.node_renderer.data_source.data['index']:
          idx = graph.node_renderer.data_source.data['index'].index(label)
          angle = plot.handles['layout_provider'].node_coordinates[idx][1]  # Y coordinate angle
          
          # Custom rotation logic: Adjust angle to keep labels upright
          #rotation = 0 if np.sin(angle) >= 0 else np.pi  # Face up
          graph.node_renderer.glyph.text_angle = 0

  def add_custom_labels(plot, element):
    """
    Adds custom labels to the Bokeh plot.
    """
    renderer = plot.handles['renderer']
    # Obtain the plot from the renderer
    bokeh_plot = plot.state

    # Create a LabelSet with specified properties
    label_set = LabelSet(
        x='x', y='y',  # The coordinates of labels (adjust these as necessary)
        text='text',  # Column containing the text of labels
        source=plot.handles['source'],
        angle=0,  # Rotation angle in radians; use 0 for horizontal
        text_align='center',
        text_baseline='middle'
    )
    
    bokeh_plot.add_layout(label_set)


  chord = hv.Chord(edges_df)
  chord.opts(
    opts.Chord(cmap='Category20', edge_cmap='Category20', edge_color=dim('source').str(), labels='index', node_color=dim('index').str(), hooks=[add_custom_labels]))


  show(hv.render(chord))  # Explicitly show the plot

def get_average_annotation_label_step(project_id):
  label_stats= {}

  annotation_df = d.get_annotations(annotator_email)
  annotations = annotation_df[project_id][0]["filledArray"]

  excluded_annotations = ("Artifact", "No Label")

  annotations = [x[0] for x in annotations if x[0] not in excluded_annotations]
  total_steps = len(annotations)

  for step, label in enumerate(annotations):
    if (label not in label_stats.keys()):
      label_stats[label] = {
        "normalized_step": step / total_steps,
        "count": 1
      }
    else:
      label_stats[label]["normalized_step"] += (step / total_steps)
      label_stats[label]["count"] += 1
    
  df = pd.DataFrame(label_stats).T.reset_index()
  df["average location"] = df.apply(lambda x: x["normalized_step"] / x["count"], axis=1)
  df = df.sort_values(by="average location").reset_index()

  def special_random(n):
    l = []
    min_val = -6
    max_val = 6

    exclude = [0, 0, 0]

    for index in range(n):
      random.choice([i for i in range(0,9) if i not in [2,5,7]])
      num = random.choice([i for i in range(min_val, max_val +1) if i not in [exclude]])
      exclude[index % 2] = num
      l.append(num)
    
    return l

  print("len", len(df))

  levels = [1, -2, 2, -3, 1, 4, -2, 7, 5, -3, -7, -6, 4, -3, 6]

  df["level"] = pd.Series(levels).T
  df = df.rename(columns={"index": "label"})
  print(df.head(100))

  print(df.to_latex(columns="average location"))

  fig, ax = plt.subplots(figsize=(18,9))

  ax.plot(df["average location"], [0,]* len(df), "-o", color="black", markerfacecolor="white");

  #ax.set_xlim(0, 1)
  ax.set_ylim(-7,7)

  for idx in range(len(df)):
      location, label, level = df["average location"][idx], df["label"][idx], df["level"][idx]

      if (label in Taxonomy["Planning"]["Classes"]):
        color = Taxonomy["Planning"]["Color"]
      elif (label in Taxonomy["Implementation"]["Classes"]):
        color = Taxonomy["Implementation"]["Color"]
      else:
        color = Taxonomy["Revision"]["Color"]

      ax.annotate(label, xy=(location, 0),
                  xytext=(location, level),
                  arrowprops=dict(arrowstyle="-",color=color, linewidth=1),
                  ha="center")

  ax.spines[["left", "top", "right", "bottom"]].set_visible(False)
  ax.spines[["bottom"]].set_position(("axes", 0.5))
  ax.yaxis.set_visible(False)
  #ax.set_title("", pad=10, loc="left", fontsize=25, fontweight="bold")

  plt.show()
  #plt.savefig("annotation_timeline.png")
  #plt.savefig("annotation_timeline.pdf", bbox_inches='tight')

def get_distribution(steps, total_steps, agg_size):
  print(steps)
  print(total_steps)
  print(agg_size)
  def aggregate(values, total_length, agg_size):
    agg = np.zeros((agg_size))

    for val in values:
      normalized = math.floor((val / total_length) * agg_size)
      agg[normalized] += 1

    agg /= len(values)
    return agg

  agg = aggregate(steps, total_steps, agg_size)

  print("agg", agg)

  x_val = np.linspace(0, 1, num=agg_size)
  dist = stats.rv_discrete(values=(x_val, agg))

  return x_val, dist

def get_information_loss_from_aggregation(project_id):
  label_stats= {}

  annotation_df = d.get_annotations(annotator_email)
  annotations = annotation_df[project_id][0]["filledArray"]

  excluded_annotations = ("Artifact", "No Label")

  annotations = [x[0] for x in annotations if x[0] not in excluded_annotations]
  total_steps = len(annotations)

  #label_stats["total_steps"] = total_steps

  for step, label in enumerate(annotations):
    if (label not in label_stats.keys()):
      label_stats[label] = {
        "normalized_step": step / total_steps,
        "count": 1,
        "steps": [step]
      }
    else:
      label_stats[label]["normalized_step"] += (step / total_steps)
      label_stats[label]["count"] += 1
      label_stats[label]["steps"].append(step)
    
  df = pd.DataFrame(label_stats).T.reset_index().rename(columns={'index': 'label'})
  df["average location"] = df.apply(lambda x: x["normalized_step"] / x["count"], axis=1)
  df = df.sort_values(by="average location").reset_index(drop=True)

  df["total_steps"] = total_steps

  agg_total_steps = np.linspace(total_steps/50, total_steps/5, num=10)
  agg_sizes = total_steps / agg_total_steps
  agg_total_steps = agg_total_steps.astype(np.int32)
  agg_sizes = agg_sizes.astype(np.int32)

  print("total", agg_total_steps)
  print("sizes", agg_sizes)

  for i, agg_size in enumerate(agg_sizes):

    name = f"tot steps: {agg_size} ; step size: {agg_total_steps[i]}"

    df[[f"x val {agg_size}", name]] = df.apply(lambda x: get_distribution(x["steps"], x["total_steps"], agg_size), axis=1, result_type="expand")

    df[name] = df[name].apply(lambda x: x.entropy())
  
  print(df.columns)

  df.to_csv("agg_sizes.csv", header=True, index=False, columns=['label', 'tot steps: 50 ; step size: 48',
       'tot steps: 25 ; step size: 97', 
       'tot steps: 16 ; step size: 146',
       'tot steps: 12 ; step size: 195',
       'tot steps: 10 ; step size: 244',
       'tot steps: 8 ; step size: 292', 
       'tot steps: 7 ; step size: 341', 
       'tot steps: 6 ; step size: 390', 
       'tot steps: 5 ; step size: 439', 
       'tot steps: 5 ; step size: 488'], float_format='%.2f')

def get_label_stats(project_id, agg_size=10):
  label_stats= {}

  annotation_df = d.get_annotations(annotator_email)
  annotation_df = annotation_df[annotation_df["project"] == project_id]
  print(annotation_df.head())
  annotation_df = annotation_df.sort_values(by="timestamp")
  annotations = annotation_df["label"].tolist()

  excluded_annotations = ("Artifact", "No Label")

  annotations = [x for x in annotations if x not in excluded_annotations]
  total_steps = len(annotations)

  #label_stats["total_steps"] = total_steps

  for step, label in enumerate(annotations):
    if (label not in label_stats.keys()):
      label_stats[label] = {
        "normalized_step": step / total_steps,
        "count": 1,
        "steps": [step]
      }
    else:
      label_stats[label]["normalized_step"] += (step / total_steps)
      label_stats[label]["count"] += 1
      label_stats[label]["steps"].append(step)
    
  df = pd.DataFrame(label_stats).T.reset_index().rename(columns={'index': 'label'})
  df["average location"] = df.apply(lambda x: x["normalized_step"] / x["count"], axis=1)
  df = df.sort_values(by="average location").reset_index(drop=True)

  df["total_steps"] = total_steps

  df[["x_val", "dist"]] = df.apply(lambda x: get_distribution(x["steps"], x["total_steps"], agg_size), axis=1, result_type="expand")

  print(df.head())

  #print(df.columns)
  #print(df.head(100))

  return df

def visualize_label_distributions(project_id, project_idx):
  label_df = get_label_stats(project_id, agg_size = 10)
  
  plot_distributions(label_df, Taxonomy["Planning"]["Classes"], save=True, show=False, fname=f"project_{project_idx}_planning_dists_project.png")
  plot_distributions(label_df, Taxonomy["Implementation"]["Classes"], save=True, show=False, fname=f"project_{project_idx}_implementation_dists.png")
  plot_distributions(label_df, Taxonomy["Revision"]["Classes"], save=True, show=False, fname=f"project_{project_idx}_revision_dists_.png")

def wasserstein_distance(dist1_pdf, dist2_pdf):
  w_distance = stats.wasserstein_distance(dist1_pdf, dist2_pdf)

  #print("uniform pdf: ", uniform_dist.pdf(x) / agg_size)
  #print("label pmf", label_dist.pmf(x))
  #print("w distance:", w_distance)

  return w_distance

def jensen_shannon_divergence(dist1_pdf, dist2_pdf):
  js_div = scipy.spatial.distance.jensenshannon(dist1_pdf, dist2_pdf)

  #print("jesen_shannon divergence: ", js_div)
  return js_div

def bhattacharya_distance(dist1_pdf, dist2_pdf):
  dict1 = {index: value for index, value in enumerate(dist1_pdf)}
  dict2 = {index: value for index, value in enumerate(dist2_pdf)}

  distance = dictances.bhattacharyya(dict1, dict2)

  return distance

def calculate_distribution_distances(project_id, project_idx, distance_fn, distance_fn_name):
  agg_size = 10
  label_df = get_label_stats(project_id, agg_size = agg_size)

  uniform_dist = scipy.stats.uniform(0, 1)

  all_labels = label_df["label"].unique()

  #label_dist = label_df[label_df["label"] == label].iloc[0]["dist"]

  x = label_df.iloc[0]["x_val"]
  normalized_uniform_pdf = uniform_dist.pdf(x) / agg_size
  
  label_df[f"{distance_fn_name} to uni"] = label_df.apply(lambda x: distance_fn(x["dist"].pmf(x["x_val"]), normalized_uniform_pdf), axis=1)

  distance_cols = []

  for label in all_labels:
    dist_name = f"{distance_fn_name} to {label}"
    distance_cols.append(dist_name)

    label_df[dist_name] = label_df.apply(lambda x: distance_fn(x["dist"].pmf(x["x_val"]), label_df[label_df["label"] == label].iloc[0]["dist"].pmf(x["x_val"])), axis=1)

  label_df[f"min label"] = label_df[distance_cols].apply(lambda x: x.nsmallest(2).idxmax().split("to ")[-1], axis=1)
  label_df[f"max label"] = label_df[distance_cols].idxmax(axis=1).apply(lambda x: x.split("to ")[-1])

  #label_df[f"max label"] = label_df[f'max label']

  #print("distances\n", label_df[["label", "w_dist_from_uni"]])
  #print("distances\n", label_df.head(100))
  #print("distances\n", label_df.columns)
  #print(label_df.to_latex(header=True, columns=["label", "min label", "max label"]))
  label_df.to_csv(f"project_{project_idx}_label_{distance_fn_name}.csv", header=True, float_format='%.2f')