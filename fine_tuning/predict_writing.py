import os
import pandas as pd
from dotenv import load_dotenv
import transformers
from transformers import LongformerConfig, LongformerForSequenceClassification, LongformerTokenizerFast, DataCollatorWithPadding, AdamW, get_scheduler
import pymongo
from pymongo import MongoClient
import matplotlib.pyplot as plt
import numpy as np
from sklearn.model_selection import train_test_split
from datasets import Dataset
import torch
from torch.utils.data import DataLoader
import numpy as np
import evaluate
from tqdm import tqdm
import time
import matplotlib.pyplot as plt

load_dotenv()

MAX_LENGTH = 4096
BATCH_SIZE = 6

debug = False

device = 'cuda' if debug == False and torch.cuda.is_available() else 'cpu'

print("device:", device)

config = LongformerConfig()

id2label = {
    1: "Idea Generation", 2: "Idea Organization", 3: "Discourse Planning",
    4: "Drafting", 5: "Lexical Chaining", 6: "Object Insertion",
    7: "Semantic", 8: "Syntactic", 9: "Lexical",
    10: "Structural", 11: "Visual", 12: "Quantitative",
    13: "Feedback", 14:"Command Insertion", 0: "Citation"
}

label2id = {
    "Idea Generation":1 , "Idea Organization": 2, "Discourse Planning": 3,
    "Drafting": 4, "Lexical Chaining": 5, "Object Insertion": 6,
    "Semantic": 7, "Syntactic": 8, "Lexical": 9,
    "Structural": 10, "Visual": 11, "Quantitative": 12,
    "Feedback": 13, "Command Insertion": 14, "Citation": 0
}

def get_dataset():
  client = MongoClient('localhost', 5001)

  db = client.dataset_db
  annotation = db.fine_tuning

  query = {}

  cursor = annotation.find(query)

  activity_df = pd.DataFrame(list(cursor))[["before_text", "writing_intention"]]

  activity_df["writing_intention"] = activity_df["writing_intention"].map(label2id)

  dataset = Dataset.from_pandas(activity_df[["before_text", "writing_intention"]])

  dataset = dataset.shuffle()
  dataset = dataset.train_test_split(test_size=0.1)

  return dataset


def tokenize(batch):
  return tokenizer(batch["before_text"], padding = 'max_length', truncation=True, max_length = MAX_LENGTH)


def plot_training(training_loss, validation_loss, training_acc, eval_acc):
  fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 3))
  ax1.set_title("Learning Curve")
  ax1.set_xlabel("Epoch")
  ax1.set_ylabel("Loss")
  #ax1.set_tight_layout()
  ax1.plot(training_loss, label='Training loss')
  ax1.plot(validation_loss, label='Validation loss')
  ax1.legend()

  ax2.set_title("Accuracy across training")
  ax2.set_xlabel("Epoch")
  ax2.set_ylabel("Accuracy")
  #ax2.tight_layout()
  ax2.plot(training_acc, label='Training accuracy')
  ax2.plot(eval_acc, label='Validation accuracy')
  ax2.legend()

  fig.tight_layout(pad=5.0)
  fig.set_size_inches(18.5, 10.5)

  #fig.show()
  fig.savefig(f"training_log/figure_{time.time()}.png")

model = LongformerForSequenceClassification.from_pretrained(
  'allenai/longformer-base-4096', 
  gradient_checkpointing=False, 
  attention_window = 512,
  id2label=id2label,
  label2id=label2id,
  num_labels = 15)
model.to(device)

tokenizer = LongformerTokenizerFast.from_pretrained('allenai/longformer-base-4096', max_length = MAX_LENGTH)

dataset = get_dataset()

tokenized_dataset = dataset.map(tokenize, batched=True)

tokenized_dataset = tokenized_dataset.remove_columns(["before_text"])
tokenized_dataset = tokenized_dataset.rename_column("writing_intention", "labels")
tokenized_dataset.set_format("torch")

data_collator = DataCollatorWithPadding(tokenizer=tokenizer)
 
tokenized_dataset_train = tokenized_dataset["train"]
tokenized_dataset_eval = tokenized_dataset["test"]


train_dataloader = DataLoader(
    tokenized_dataset_train, shuffle=True, batch_size=BATCH_SIZE, collate_fn=data_collator
)

eval_dataloader = DataLoader(
    tokenized_dataset_eval, shuffle=False, batch_size=BATCH_SIZE, collate_fn=data_collator
)

for batch in train_dataloader:
    break
print({k: v.shape for k, v in batch.items()})

num_epochs = 10
num_training_steps = len(train_dataloader) * num_epochs
optimizer = AdamW(model.parameters(), lr=5e-5)
lr_scheduler = get_scheduler(
    "linear",
    optimizer=optimizer,
    num_warmup_steps=0,
    num_training_steps=num_training_steps,
)

progress_bar = tqdm(range(num_training_steps))

train_loss=[]
train_acc = []
eval_loss = []
eval_acc = []
start = time.time()


for epoch in range(num_epochs):

  train_loss_per_epoch = 0
  train_acc_per_epoch = 0
  eval_loss_per_epoch = 0
  eval_acc_per_epoch = 0

  with tqdm(train_dataloader, unit = "batch") as training_epoch:
    training_epoch.set_description(f"Training Epoch {epoch}")

    for step, inputs in enumerate (training_epoch):
      inputs = inputs.to(device)
      input_ids = inputs["input_ids"]
      attention_mask = inputs["attention_mask"]
      labels = inputs['labels']

      # forward pass
      optimizer.zero_grad()
      output = model.forward(input_ids=input_ids, attention_mask=attention_mask, labels=labels)

      loss, logits = output[:2]

      # get the loss
      #loss = criterion (loss, labels) # TODO Implement by yourself
      train_loss_per_epoch += loss.item()
      # calculate gradients
      loss.backward ()
      # update weights
      optimizer.step()
      train_acc_per_epoch += (logits.argmax(1) == labels).sum().item()

  # adjust the learning rate
  lr_scheduler.step()
  train_loss_per_epoch /= len(train_dataloader)
  train_acc_per_epoch /= (len(train_dataloader)*BATCH_SIZE)
  eval_loss_per_epoch = 0
  eval_acc_per_epoch = 0

  with tqdm(eval_dataloader, unit ="batch") as eval_epoch:
    eval_epoch.set_description(f"Evaluation Epoch {epoch}")
    # ... TODO Implement by yourself
    for step, inputs in enumerate(eval_epoch):
      inputs = inputs.to(device)
      input_ids = inputs["input_ids"]
      attention_mask = inputs["attention_mask"]
      labels = inputs ['labels']

      with torch.no_grad():
        output = model.forward(input_ids=input_ids, attention_mask=attention_mask, labels=labels)

      loss = output[0]
      logits = output[1]
      #loss = criterion (loss, labels)
      eval_loss_per_epoch += loss.item ()
      eval_acc_per_epoch += (logits.argmax(1) == labels).sum().item()

  eval_loss_per_epoch /= (len(eval_dataloader))
  eval_acc_per_epoch /= (len(eval_dataloader)*BATCH_SIZE)

  train_loss.append(train_loss_per_epoch)
  eval_loss.append(eval_loss_per_epoch)

  train_acc.append(train_acc_per_epoch)
  eval_acc.append(eval_acc_per_epoch)

  plot_training(train_loss, eval_loss, train_acc, eval_acc)
  print("after plotting losses")

  print (f'\tTrain Loss: {train_loss_per_epoch:.3f} | Train Acc: { train_acc_per_epoch * 100 :.2f}%')
  print (f'\tEval Loss: {eval_loss_per_epoch:.3f} | Eval Acc: { eval_acc_per_epoch * 100 :.2f}%')
  print (f'Time: {(time.time()-start)/60:.3f} minutes')

