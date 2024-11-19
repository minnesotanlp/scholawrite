import math

import numpy as np
import pandas as pd
import joypy
import seaborn as sns
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

from taxonomy import Taxonomy, RELEVANT_CLASSES

plt.rcParams.update({'font.size': 16})

def gantt_chart(spans, durations, start_times, categories, colors, rounded=False, filepath=None, save=False):
  base_height = 1
  interval_height = 0.5 
  fig_height = len(categories) * interval_height + base_height
  fig, ax = plt.subplots(figsize=(10, fig_height))

  spans = [x for x in spans if x in categories]

  for i, color in enumerate(colors):
      ax.axhspan(len(colors) - i - 1.5, len(colors) - i - 0.5, facecolor=color, alpha=0.3)

  for i, span in enumerate(spans):
      y_position = len(categories) - categories.index(span) - 1

      ax.barh(y_position, durations[i], left=start_times[i], color='black')
  
  ax.set_yticks(np.arange(len(categories)))
  ax.set_yticklabels(reversed(categories))

  ax.set_xlabel('Step')
  ax.set_ylabel('Activity')
  ax.set_title('Writing activity per step')

  # remove vertical padding in chart
  ax.set_ylim(-0.5, len(categories) - 0.5)

  plt.tight_layout()

  if (save):
    if (filepath is None):
       raise Exception("Provide filepath to save figure")
    plt.savefig(filepath, bbox_inches="tight")
  else:  
    plt.show()

def plot_one_distribution(label_df, label, ax=None):
  #print("label", label)
  try:
    row = label_df[label_df["label"] == label].iloc[0]
  except:
    return

  #print("row:", row)

  x_val = row["x_val"]
  dist = row["dist"]

  pmf = dist.pmf(x_val)

  if (ax is None):
    fig, ax = plt.subplots(1, 1)

  ax.plot(x_val, pmf, 'ro', ms=8, mec='r')
  ax.vlines(x_val, 0, pmf, colors='r', linestyles='-', lw=2)

  ax.figure.set_size_inches(10, 8)

  if (ax is None):
    plt.title(f"{label} Distribution")
    plt.ylabel('Probability')
    plt.show()
  else:
    ax.set_title(f"{label} Distribution")
    ax.set_ylabel('Probability')

def plot_distributions(label_df, labels, save=False, show=True, fname="fig.png"):
  n = len(labels)

  #print(n)

  if (n <= 2):
    fig, axes = plt.subplots(1, 2)
  else:
    fig, axes = plt.subplots(math.ceil(n/2), 2)

  #print("axes:", axes)
  #print("shape", n, axes.shape)

  rows, cols = axes.shape

  for i, label in enumerate(labels):
    row = math.floor(i / cols)
    col = i % cols

    #print(row, col)
    plot_one_distribution(label_df, label, ax=axes[row][col])
  
  #sys.stdout.flush()
  plt.tight_layout()

  if (show):
    plt.show()
  if (save):
    plt.savefig(fname)

def overlay_distributions(label_df, labels, name, project_idx=1, save=False, show=True, fname="fig.png"):

  n = 10  # Number of distributions
  np.random.seed(42)

  print(label_df.columns)

  label_df = label_df.sort_values(by="average location", ascending=False)

  labels = [x for x in label_df["label"].unique() if x in labels]

  plt.figure()

  # Create a DataFrame to store all distributions
  data = []
  for i, label in enumerate(labels):
    row = label_df[label_df["label"] == label].iloc[0]
    x_val = row["x_val"]
    #dist = row["dist"]

    vals = row["steps"] / row["total_steps"]

    hist_values, bin_edges = np.histogram(vals, bins=10, range=(0, 1), density=True)


    hist_values = np.sqrt(hist_values)
    hist_values *= 0.25
    
    bin_centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])
    
    shift = i * 0.6  # Adjust this value for the vertical spacing

    #color = f"C{i}"

    if label in Taxonomy["Planning"]["Classes"]:
      color = Taxonomy["Planning"]["Color"]
    if label in Taxonomy["Implementation"]["Classes"]:
      color = Taxonomy["Implementation"]["Color"]
    if label in Taxonomy["Revision"]["Classes"]:
      color = Taxonomy["Revision"]["Color"]

    plt.plot(bin_centers, hist_values + shift, color=color)
    
    plt.fill_between(bin_centers, shift, hist_values + shift, color=color, alpha=0.4)
    
    # Add the label for each group
    #plt.text(bin_centers -0.5, shift + 0.02, label, fontsize=12)
    plt.text(-0.05, shift + 0.02, label, ha='right')

  #plt.title(f"Project {project_idx}", fontsize=16)
  plt.yticks([])
  plt.xticks(fontsize=12)

  plt.subplots_adjust(left=0.25)

  plt.tight_layout()

  #plt.show()
  plt.savefig(f"project_{project_idx}_distributions.pdf")
  plt.close()

def plot_distance(fname, project_idx):
  df = pd.read_csv(fname)

  df = df[["label", "w_dist to uni"]]
  df = df.sort_values(by="w_dist to uni")

  def det_color(label):
    if label in Taxonomy["Planning"]["Classes"]:
      return Taxonomy["Planning"]["Color"]
    elif label in Taxonomy["Implementation"]["Classes"]:
      return Taxonomy["Implementation"]["Color"]
    elif label in Taxonomy["Revision"]["Classes"]:
      return Taxonomy["Revision"]["Color"]
    else:
      return "#000000"

  colors = df['label'].apply(det_color)

  df.plot(kind='barh', x='label', y='w_dist to uni', color=colors, legend=False)

  # Customize the plot
  #plt.title(f"Project {project_idx}")
  plt.grid(axis='x')
  plt.tight_layout()

  # Show the plot
  #plt.show()
  plt.savefig(f"dist_to_uni/project_{project_idx}_label_w_dist.pdf")

def plot_avg_distance():
  fname = "project_{}_label_w_dist.csv"
  df1 = pd.read_csv(fname.format(0))
  df2 = pd.read_csv(fname.format(1))
  df3 = pd.read_csv(fname.format(2))
  df4 = pd.read_csv(fname.format(3))
  df5 = pd.read_csv(fname.format(4))
  combined_df = pd.concat([df1, df2, df3, df4, df5])

  df = combined_df.groupby('label', as_index=False)['w_dist to uni'].mean()

  df = df[["label", "w_dist to uni"]]
  df = df.sort_values(by="w_dist to uni")

  df = df[df["label"].isin(RELEVANT_CLASSES)]

  def det_color(label):
    if label in Taxonomy["Planning"]["Classes"]:
      return Taxonomy["Planning"]["Color"]
    elif label in Taxonomy["Implementation"]["Classes"]:
      return Taxonomy["Implementation"]["Color"]
    elif label in Taxonomy["Revision"]["Classes"]:
      return Taxonomy["Revision"]["Color"]
    else:
      return "#000000"

  colors = df['label'].apply(det_color)

  df.plot(kind='barh', x='label', y='w_dist to uni', color=colors, legend=False)

  # Customize the plot
  #plt.title(f"Project {project_idx}")
  plt.grid(axis='x')
  plt.tight_layout()

  # Show the plot
  #plt.show()
  plt.savefig(f"avg_w_dist_to_uni.pdf")
  plt.savefig(f"avg_w_dist_to_uni.pdf")
