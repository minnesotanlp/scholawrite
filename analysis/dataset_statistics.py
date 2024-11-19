import dataset
import os
import glob

from dataset import KeystrokeDataset
import pandas as pd
from pymongo import MongoClient
import matplotlib.pyplot as plt
import data
from diff_utils import get_word_diff

from taxonomy import RELEVANT_CLASSES

def get_dataset():
  client = MongoClient("localhost", 5001)
  db = client["flask_db"]

  query = {}
  cursor = db.visual_data.find(query)
  df = pd.DataFrame(list(cursor))

  df = df.drop(columns=["label"])

  query = {"annotatorEmail": "update"}
  cursor = db.annotation.find(query)

  ann_df = pd.DataFrame(list(cursor))
  ann_df = ann_df.drop(columns=["_id", "annotatorEmail"])
  ann_df = ann_df.T.reset_index()
  ann_df.columns = ["project", "labels"]
  ann_df["labels"] = ann_df["labels"].apply(lambda x: x["filledArray"])
  ann_df = ann_df.explode("labels")

  ann_df = ann_df.sort_values(by="project", kind="stable").reset_index()
  df = df.sort_values(by=["project", "timestamp"]).reset_index()

  df["label"] = ann_df["labels"]

  print(df.columns)

  df = df.drop(columns=["level_0", "_id", "state", "line", "explanation", "accept", "start", "cb", "assistError", "selected_text", "target", "suggestion", "clipboard", "editingLines", "message", "changes", "index", "text"])


  def get_before_after(diff_array):
    before_text = ""
    after_text = ""

    for arr in diff_array:
      op = arr[0]
      text = arr[1]

      if op == -1: 
        before_text += text
      elif op == 1:  
        after_text += text
      elif op == 0:  
        before_text += text
        after_text += text
    
    return before_text, after_text

  print(len(df))

  df = df[df["label"].apply(lambda x: len(x) == 1)]
  print(len(df))

  df["label"] = df["label"].apply(lambda x: x[0])

  df = df[df["revision"].apply(lambda x: len(x) < 700)]

  print(len(df))

  df[['before_text', 'after_text']] = df['revision'].apply(lambda diff: pd.Series(get_before_after(diff)))
  #df = df.drop(columns=["revision"])

  df = df[df["label"].isin(RELEVANT_CLASSES)]

  df["label"] = df["label"].replace({"Textual Style": "Linguistic Style"})
  df["label"] = df["label"].replace({"Visual Style":"Visual Formatting"})

  return df

df = get_dataset()
df.loc[df["project"] == "6578ec8845504beacf9d3dc7", "project"] = "6500d748909490ecba83e811"

# projects

project_ids = df["project"].unique()

# num authors per paper

len_authors = []

for project_id in project_ids:
  df_proj = df[df["project"] == project_id]
  authors = df_proj["username"].unique()
  print(authors)

len_authors = [1, 1, 1, 1, 9]

# number of time spans per project

for project_id in project_ids:
  df_proj = df[df["project"] == project_id]
  print("num time steps", len(df_proj))

for i, project in enumerate(os.listdir("participant_papers")):
  if (project == ".DS_Store"):
    continue

  chars = 0
  words = 0

  for file in glob.glob(f"participant_papers/{project}/**/*.tex", recursive=True):
    with open(file, 'r') as f:
      for line in f.readlines():
        chars += len(line)
        words += len(line.split())
      
  print(file, chars, words)

for project_id in project_ids:
  df_proj = df[df["project"] == project_id]

  def do_word_diff(activity_df):
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
  
  print(do_word_diff(df_proj))




