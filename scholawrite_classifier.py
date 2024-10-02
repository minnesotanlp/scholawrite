import os
hf_token = os.getenv("HF_TOKEN")

import pandas as pd
from sklearn.preprocessing import LabelEncoder

from transformers import BertTokenizer, BertForSequenceClassification
import torch

import datasets
from datasets import Dataset, DatasetDict

from transformers import TrainingArguments, Trainer

import numpy as np

# LINGHE, can you tell me which projects are done annotating, and which project is who's paper?
project_ids = [
  "6500d748909490ecba83e811",  # Debarati's project part 1, Done
  "6578ec8845504beacf9d3dc7",  # Debarati's project part 2, Done
  "654682f220e7d557c7e67cff",  # Anna's project, Done
  "656a440644dec9f71f2dee44",  # Zae's project, Done
  #"640e22cae918523bcee8ca5e", # karin's project, Done
  #"656fadd102ae94a7686aae62"  # Artifact paper, Not done
]

Taxonomy = {
  "Planning": {
    "Classes": ("Idea Generation", "Idea Organization", "Section Planning"),
    "Color": "#b0d184"
  },
  "Implementation": {
    "Classes": ("Text Production", "Object Insertion", "Cross-reference", "Citation Integration", "Macro Insertion"),
    "Color": "#84bcd1"
  },
  "Revision": {
    "Classes": ("Fluency", "Coherence", "Structural", "Clarity", "Textual Style", "Scientific Accuracy", "Visual Style"),
    "Color": "#9584d1"
  },
  "Other": {
    "Classes": ("Artifact", "No Label", "Ambiguous"),
    "Color": "#d1849a"
  }
}

RELEVANT_CLASSES = Taxonomy["Planning"]["Classes"] + Taxonomy["Implementation"]["Classes"] + Taxonomy["Revision"]["Classes"]
print(RELEVANT_CLASSES)


class ScholawriteDataset():
  def __init__(self):
    self.load_csv()
    self.le = LabelEncoder()

  def load_csv(self):
    self.df = datasets.load_dataset('minnesotanlp/scholawrite', 
                                    revision='classifier')["train"].to_pandas()

    self.df = self.df[["timestamp", "before_text", "after_text", "project", "label"]]

    print(self.df.head())

  def preprocess_one_project(self, project_id):
    proj_df = self.df[self.df["project"] == project_id]

    def is_label_relevant(x):
      return x in RELEVANT_CLASSES

    proj_df = proj_df[proj_df["label"].apply(lambda x: is_label_relevant(x))]

    proj_df["label"] = self.le.fit_transform(proj_df["label"])

    proj_df = proj_df.sort_values(by="timestamp", ascending=False)
    proj_df = proj_df.reset_index(drop=True)
    proj_df = proj_df.drop(columns=["timestamp", "project"])

    #proj_df["revision"] = proj_df["revision"].apply(lambda x: ast.literal_eval(x))

    return proj_df

d = ScholawriteDataset()
dataset_df = d.preprocess_one_project(project_ids[0])

dataset_df.head()


def get_bert_model_tokenizer():
  tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
  model = BertForSequenceClassification.from_pretrained('bert-base-uncased', num_labels=len(RELEVANT_CLASSES))

  print("num_labels", len(RELEVANT_CLASSES))

  # add custom tokens to vocab
  tokenizer.add_tokens("<INPUT>")  # start input
  tokenizer.add_tokens("</INPUT>") # end input
  tokenizer.add_tokens("<BT>")     # before text
  tokenizer.add_tokens("</BT>")    # before text
  tokenizer.add_tokens("<PWA>")    # start previous writing action
  tokenizer.add_tokens("</PWA>")   # end previous writing action

  model.resize_token_embeddings(len(tokenizer))

  return model, tokenizer

bert_model, bert_tokenizer = get_bert_model_tokenizer()

def add_intention_inference_instruction_input(dataset_df, include_prev_label=False):
  dataset_df["instruction input"] = "<INPUT>" + "<BT>" + dataset_df["before_text"] + "</BF> "

  if (include_prev_label):
    dataset_df["prev_label"] = dataset_df["label"].shift(1).fillna("none")
    dataset_df["instruction input"] += "<PWA>" + dataset_df["prev_label"] + "</PWA> "
    dataset_df.remove_columns(columns=["prev_label"])

  dataset_df["instruction input"] += "</INPUT>"

add_intention_inference_instruction_input(dataset_df)
dataset_df.head()


#ds = Dataset.from_pandas(dataset_df.iloc[0:10])
ds = Dataset.from_pandas(dataset_df)

def tokenize_function(examples):
    return bert_tokenizer(examples["instruction input"], padding="max_length", truncation=True)

tokenized_ds = ds.map(tokenize_function, batched=True)

tokenized_ds = tokenized_ds.remove_columns(["instruction input", "before_text", "after_text"])
tokenized_ds.set_format("torch")
tokenized_ds = tokenized_ds.train_test_split(test_size=0.2)

train_ds = tokenized_ds["train"]
eval_ds = tokenized_ds["test"]


training_args = TrainingArguments(
    output_dir="./results",
    evaluation_strategy="epoch",
    learning_rate=2e-5,
    per_device_train_batch_size=8,
    per_device_eval_batch_size=8,
    num_train_epochs=10,
    weight_decay=0.01
)

trainer = Trainer(
    model=bert_model,
    args=training_args,
    train_dataset=train_ds,
    eval_dataset=eval_ds
)

trainer.train()

# prompt: predict with the model on the eval dataset and show output in sheet

predictions = trainer.predict(eval_ds)
predicted_labels = np.argmax(predictions.predictions, axis=1)

eval_df = eval_ds.to_pandas()
eval_df["predicted_label"] = predicted_labels
eval_df["predicted_label"] = eval_df["predicted_label"].apply(lambda x: d.le.inverse_transform([x])[0])
eval_df["label"] = eval_df["label"].apply(lambda x: d.le.inverse_transform([x])[0])

sheet = sheets.InteractiveSheet(df=eval_df.astype(str))

