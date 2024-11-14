import os 
import numpy as np
import matplotlib.pyplot as plt
from taxonomy import Taxonomy, RELEVANT_CLASSES

ross = False
#src_dir = "iterative_inference_output_seed_base"
src_dir = "gpt4o-inference/iterative_writing_cls_and_gen/seed_base/iterative_class_results"

intentions = []

for file in os.listdir(src_dir):
  if (ross and "intention" not in file):
    continue

  with open(f"{src_dir}/{file}", "r") as f:
    intentions.append(f.read().strip())

ones = [1] * len(intentions)
start_times = [i for i in range(len(intentions))]
colors = []
categories = RELEVANT_CLASSES

def get_color(wi):
  if (wi in Taxonomy["Planning"]["Classes"]):
    return Taxonomy["Planning"]["Color"]
  elif (wi in Taxonomy["Implementation"]["Classes"]):
    return Taxonomy["Implementation"]["Color"]
  elif (wi in Taxonomy["Revision"]["Classes"]):
    return Taxonomy["Revision"]["Color"]
  else:
    return "#000000"
  
colors = [get_color(x) for x in categories]


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

gantt_chart(intentions, ones, start_times, categories, colors, filepath="llama_intention.png", save=True)