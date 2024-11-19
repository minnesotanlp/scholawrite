import os

from dotenv import load_dotenv
from dataset import KeystrokeDataset
import pandas as pd
from pymongo import MongoClient
from datasets import Dataset
from huggingface_hub import login

from taxonomy import RELEVANT_CLASSES

#pd.set_option('display.max_rows', None)
load_dotenv()

print("second")
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
login(token=HUGGINGFACE_TOKEN)

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

df = df.drop(columns=["level_0", "_id", "state", "line", "username", "explanation", "accept", "start", "cb", "assistError", "selected_text", "target", "suggestion", "clipboard", "editingLines", "message", "changes", "index", "text"])

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
df = df.drop(columns=["revision"])

df = df[df["label"].isin(RELEVANT_CLASSES)]

df["label"] = df["label"].replace({"Textual Style": "Linguistic Style"})
df["label"] = df["label"].replace({"Visual Style":"Visual Formatting"})

full_ds = Dataset.from_pandas(df)
full_ds = full_ds.train_test_split(test_size=0.2, seed = 100)

full_ds.push_to_hub("minnesotanlp/scholawrite")