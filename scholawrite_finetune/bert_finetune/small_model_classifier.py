import os
from datetime import datetime
from dotenv import load_dotenv

import torch
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from transformers import BertTokenizer, BertForSequenceClassification, RobertaTokenizer, RobertaForSequenceClassification
import datasets
from datasets import Dataset, DatasetDict, load_dataset
import matplotlib.pyplot as plt
import numpy as np
from sklearn.utils.class_weight import compute_class_weight
from transformers import Trainer
from huggingface_hub import login

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
print("device", device)

load_dotenv()

HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
login(token=HUGGINGFACE_TOKEN)

#model_name = "BERT"
model_name = "ROBERTA"


TOTAL_CLASSES = 15

class ScholawriteDataset():
  def __init__(self):
    self.load_csv()
    self.le = LabelEncoder()

  def load_csv(self):
    #self.df = datasets.load_dataset('minnesotanlp/scholawrite', revision='classifier')["train"].to_pandas()
    self.df = datasets.load_dataset("minnesotanlp/scholawrite", revision="anonymous_data")["train"].to_pandas()

    self.df = self.df[["timestamp", "before text", "after text", "project", "label"]]
    self.df["label"] = self.le.fit_transform(self.df["label"])

    print(self.df.head())

  def preprocess_one_project(self, project_id):
    proj_df = self.df[self.df["project"] == project_id]

    proj_df["label"] = self.le.fit_transform(proj_df["label"])

    proj_df = proj_df.sort_values(by="timestamp", ascending=False)
    proj_df = proj_df.reset_index(drop=True)
    proj_df = proj_df.drop(columns=["timestamp", "project"])

    return proj_df

def get_model_tokenizer(model_name):
  if (model_name == "BERT"):
    tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
    model = BertForSequenceClassification.from_pretrained('bert-base-uncased', num_labels=TOTAL_CLASSES)
  elif (model_name == "ROBERTA"):
    tokenizer = RobertaTokenizer.from_pretrained('FacebookAI/roberta-base')
    model = RobertaForSequenceClassification.from_pretrained('FacebookAI/roberta-base', num_labels=TOTAL_CLASSES)
  else:
    raise Exception("No such model name")

  print("num_labels", TOTAL_CLASSES)

  # add custom tokens to vocab
  tokenizer.add_tokens("<INPUT>")  # start input
  tokenizer.add_tokens("</INPUT>") # end input
  tokenizer.add_tokens("<BT>")     # before text
  tokenizer.add_tokens("</BT>")    # before text
  tokenizer.add_tokens("<PWA>")    # start previous writing action
  tokenizer.add_tokens("</PWA>")   # end previous writing action

  model.resize_token_embeddings(len(tokenizer))

  return model, tokenizer

def add_intention_inference_instruction_input(dataset_df, include_prev_label=False):
  dataset_df["instruction input"] = "<INPUT>" + "<BT>" + dataset_df["before text"] + "</BF> "

  if (include_prev_label):
    dataset_df["prev_label"] = dataset_df["label"].shift(1).fillna("none")
    dataset_df["instruction input"] += "<PWA>" + dataset_df["prev_label"] + "</PWA> "
    dataset_df.remove_columns(columns=["prev_label"])

  dataset_df["instruction input"] += "</INPUT>"


model, tokenizer = get_model_tokenizer(model_name)

#full_ds = load_dataset("minnesotanlp/scholawrite")
#train_ds = full_ds["train"].to_pandas()
#test_ds = full_ds["test"].to_pandas()

le = LabelEncoder()
full_ds = datasets.load_dataset("minnesotanlp/scholawrite", revision="anonymous_data")
train_ds = full_ds["train"].to_pandas()
test_ds = full_ds["test"].to_pandas()

#train_ds = train_ds[["timestamp", "before text", "after text", "project", "label"]]
train_ds["label"] = le.fit_transform(train_ds["label"])
test_ds["label"] = le.fit_transform(test_ds["label"])

add_intention_inference_instruction_input(train_ds)
add_intention_inference_instruction_input(test_ds)

#train_ds = Dataset.from_pandas(train_ds).select(range(100))
#test_ds = Dataset.from_pandas(test_ds).select(range(100))

train_ds = Dataset.from_pandas(train_ds)
test_ds = Dataset.from_pandas(test_ds)

def tokenize_function(examples):
    return tokenizer(examples["instruction input"], padding="max_length", truncation=True)

train_ds = train_ds.map(tokenize_function, batched=True)
train_ds = train_ds.remove_columns(["instruction input", "before text", "after text"])
train_ds.set_format("torch")

test_ds = test_ds.map(tokenize_function, batched=True)
test_ds = test_ds.remove_columns(["instruction input", "before text", "after text"])
test_ds.set_format("torch")

#print(train_ds["label"])
#raise Exception

def dataset_statistics(dataset, dataset_name):
  labels, counts = dataset["label"].unique(return_counts=True)

  labels = d.le.inverse_transform(labels.tolist())
  counts = counts.tolist()

  tup = zip(labels, counts)
  tup = sorted(tup, key=lambda x: x[1], reverse=True)
  labels, counts = zip(*tup)

  print(labels)
  print(counts)

  fig, ax = plt.subplots()
  ax.bar(labels, counts)
  ax.set_xticklabels(labels, rotation=45, ha='right')  # 'ha' means horizontal alignment
  plt.title(dataset_name)
  plt.show()
  fig.tight_layout()
  plt.savefig(f"{dataset_name}_dataset_label_dist.png")

  return labels, counts

#dataset_statistics(train_ds, "train")
#dataset_statistics(eval_ds, "eval")

train_labels = np.array(train_ds["label"])

all_train_labels = np.arange(0, TOTAL_CLASSES)

print("all_train_labels: ", all_train_labels)

train_labels = np.concatenate((train_labels, np.array(all_train_labels)), casting="same_kind")

class_weights = compute_class_weight(class_weight="balanced", classes=np.unique(train_labels), y=train_labels)
class_weights = torch.tensor(class_weights, dtype=torch.float)
print(class_weights)
class_weights /= class_weights.sum()
print(class_weights.sum())
class_weights = class_weights.to(device)

class ScholawriteTrainer(Trainer):
  def compute_loss(self, model, inputs, return_outputs=False):
    labels = inputs.get("labels")
    outputs = model(**inputs)
    logits = outputs.get("logits")

    loss_fct = torch.nn.CrossEntropyLoss(weight=class_weights)
    loss = loss_fct(logits.view(-1, self.model.config.num_labels), labels.view(-1))
    return (loss, outputs) if return_outputs else loss

from transformers import TrainingArguments, Trainer

training_args = TrainingArguments(
    output_dir=f"./results/{model_name}_run_final",
    evaluation_strategy="epoch",
    learning_rate=2e-5,
    per_device_train_batch_size=8,
    per_device_eval_batch_size=8,
    num_train_epochs=10,
    weight_decay=0.01
)

trainer = ScholawriteTrainer(
    model=model,
    args=training_args,
    train_dataset=train_ds,
    eval_dataset=test_ds
)


if False:
  trainer.train()
else:
  ##trainer.model = trainer.model.from_pretrained(training_args.output_dir + "/checkpoint-30760")
  pass

# prompt: predict with the model on the eval dataset and show output in sheet

import numpy as np

predictions = trainer.predict(test_ds)
predicted_labels = np.argmax(predictions.predictions, axis=1)

eval_df = test_ds.to_pandas()
eval_df["predicted_label"] = predicted_labels
eval_df["predicted_label"] = eval_df["predicted_label"].apply(lambda x: le.inverse_transform([x])[0])
eval_df["label"] = eval_df["label"].apply(lambda x: le.inverse_transform([x])[0])

eval_df.to_csv(f"{model_name}_run_final.csv")

def calculate_metrics(eval):
  from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

  y_true = eval["label"]
  y_pred = eval["predicted_label"]

  accuracy = accuracy_score(y_true, y_pred)

  print("acc", accuracy)

calculate_metrics(eval_df)
