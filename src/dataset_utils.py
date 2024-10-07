import matplotlib.pyplot as plt
import datasets
from datasets import Dataset
from sklearn.preprocessing import LabelEncoder

import args

le = LabelEncoder()

def get_scholawrite_dataset():
  df = datasets.load_dataset('minnesotanlp/scholawrite', revision='classifier')["train"].to_pandas()

  df = df[["timestamp", "before_text", "after_text", "project", "label"]]

  return df

def preprocess_one_project(df, project_id, relevant_classes):
  proj_df = df[df["project"] == project_id]

  def is_label_relevant(x):
    return x in relevant_classes

  proj_df = proj_df[proj_df["label"].apply(lambda x: is_label_relevant(x))]

  #proj_df["label"] = le.fit_transform(proj_df["label"])

  proj_df = proj_df.sort_values(by="timestamp", ascending=False)
  proj_df = proj_df.reset_index(drop=True)
  proj_df = proj_df.drop(columns=["timestamp", "project"])

  #proj_df["revision"] = proj_df["revision"].apply(lambda x: ast.literal_eval(x))

  return proj_df

def preprocess_many_projects(df, relevant_project_ids, relevant_classes):
  proj_df = df[df["project"].isin(relevant_project_ids)]

  def is_label_relevant(x):
    return x in relevant_classes

  proj_df = proj_df[proj_df["label"].apply(lambda x: is_label_relevant(x))]

  #proj_df["label"] = le.fit_transform(proj_df["label"])

  #proj_df = proj_df.sort_values(by="timestamp", ascending=False)
  #proj_df = proj_df.reset_index(drop=True)
  proj_df = proj_df.drop(columns=["timestamp", "project"])

  #proj_df["revision"] = proj_df["revision"].apply(lambda x: ast.literal_eval(x))

  return proj_df

def add_special_tokens(model, tokenizer):
  tokenizer.add_tokens("<INPUT>")   # start input
  tokenizer.add_tokens("</INPUT>")  # end input
  tokenizer.add_tokens("<BT>")      # before text
  tokenizer.add_tokens("</BT>")     # before text
  tokenizer.add_tokens("<PWA>")     # start previous writing action
  tokenizer.add_tokens("</PWA>")    # end previous writing action
  tokenizer.add_tokens("<WI>")     # current writing intention
  tokenizer.add_tokens("</WI>")    # current writing intention
  tokenizer.add_special_tokens({'pad_token': '[PAD]'})    

  print("len", len(tokenizer))

  model.resize_token_embeddings(len(tokenizer))

def get_intention_inference_instruction_dataset(dataset_df, tokenizer, include_prev_label=False):
  dataset_df["instruction input"] = "<INPUT>" + "<BT>" + dataset_df["before_text"] + "</BF> "

  if (include_prev_label):
    dataset_df["prev_label"] = dataset_df["label"].shift(1).fillna("none")
    dataset_df["instruction input"] += "<PWA>" + dataset_df["prev_label"] + "</PWA> "
    dataset_df.remove_columns(columns=["prev_label"])

  dataset_df["instruction input"] += "</INPUT>"

def get_writing_prediction_instruction_dataset(dataset_df, tokenizer, include_prev_label=False):
  dataset_df["instruction input"] = "<INPUT>" + "<BT>" + dataset_df["before_text"] + "</BF> " + "<WI>" + dataset_df["label"] + "</WI>"

  if (include_prev_label):
    dataset_df["prev_label"] = dataset_df["label"].shift(1).fillna("none")
    dataset_df["instruction input"] += "<PWA>" + dataset_df["prev_label"] + "</PWA> "
    dataset_df.remove_columns(columns=["prev_label"])

  dataset_df["instruction input"] += "</INPUT>"

def get_dataset_from_df(dataset_df, tokenizer):
  ds = Dataset.from_pandas(dataset_df)

  def tokenize_function(examples):
      return tokenizer(examples["instruction input"], padding="max_length", truncation=True)

  tokenized_ds = ds.map(tokenize_function, batched=True)

  tokenized_ds = tokenized_ds.remove_columns(["instruction input", "before_text", "after_text"])
  tokenized_ds.set_format("torch")
  tokenized_ds = tokenized_ds.train_test_split(test_size=0.2)

  return tokenized_ds

def tokenize_dataset(ds):
  def tokenize_function(examples):
      return tokenizer(examples["instruction input"], padding="max_length", truncation=True)

  tokenized_ds = ds.map(tokenize_function, batched=True)

  tokenized_ds = tokenized_ds.remove_columns(["instruction input", "before_text", "after_text"])
  tokenized_ds.set_format("torch")
  tokenized_ds = tokenized_ds.train_test_split(test_size=0.2)

  return tokenized_ds


def get_dataset_statistics(dataset):
  labels, counts = dataset["label"].unique(return_counts=True)

  labels = d.le.inverse_transform(labels.tolist())
  counts = counts.tolist()

  tup = zip(labels, counts)
  tup = sorted(tup, key=lambda x: x[1], reverse=True)
  labels, counts = zip(*tup)

  fig, ax = plt.subplots()
  ax.bar(labels, counts)
  ax.set_xticklabels(labels, rotation=45, ha='right')  # 'ha' means horizontal alignment
  plt.title(dataset_name)
  plt.show()
  fig.tight_layout()
  plt.savefig(f"{args.MEDIA_DIR}/dataset_label_dist.png")

  return labels, counts
