import os
import pandas as pd

output_dir = "../outputs/llama8_meta_output"
# output_dir = "../outputs/gpt4o_output"
# output_dir = "../outputs/llama8_SW_output"

seeds = ["seed1", "seed2", "seed3", "seed4"]

for seed in seeds:
  path = f"{output_dir}/{seed}/intention"

  filenames = os.listdir(path)
  sorted_filenames = sorted(filenames, key=lambda x: int(x.split('_')[2].replace(".txt", "")))

  predicted_labels = []

  for f in sorted_filenames:
    with open(path + "/" + f, 'r') as fp:
      intention = fp.read().rstrip()

    predicted_labels.append(intention)
  
  df = pd.DataFrame(predicted_labels)
  print(len(df[0].unique()))
  # print(df[0].value_counts())



