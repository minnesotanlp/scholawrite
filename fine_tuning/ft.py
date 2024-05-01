import os
import pandas as pd
from dotenv import load_dotenv
import transformers
from transformers import AutoModelForCausalLM, AutoTokenizer
import pymongo
from pymongo import MongoClient
import matplotlib.pyplot as plt
import numpy as np
import torch

load_dotenv()

hf_api_key = os.environ["HUGGINGFACE_API_KEY"]

debug = False
device = 'cuda' if debug == False and torch.cuda.is_available() else 'cpu'

checkpoint = "HuggingFaceH4/zephyr-7b-beta"
model = AutoModelForCausalLM.from_pretrained(checkpoint)
model.to(device)
model.eval()

tokenizer = AutoTokenizer.from_pretrained(checkpoint)

def get_dataset():
  client = MongoClient('localhost', 5001)

  db = client.dataset_db
  annotation = db.fine_tuning
  query = {}
  cursor = annotation.find(query)

  activity_df = pd.DataFrame(list(cursor))

  idx = 30

  before_text = activity_df["before_text"].iloc[idx]
  diff_arr = activity_df["diff_array"]
  writing_intention = activity_df["writing_intention"].iloc[idx]

  diff_text = ""

  for diff in diff_arr.iloc[0]:
    diff = diff[:2]
    key = diff[0]
    text = diff[1]

    if (key == 0):
      diff_text += text
    elif(key == 1):
      diff_text += "[ADD]"
      diff_text += text
      diff_text += "[/ADD]"
    elif(key == -1):
      diff_text += "[DEL]"
      diff_text += text
      diff_text += "[/DEL]"
    
  verbalizer = "Draft a paragraph of full sentences in the body of the paper"

  return verbalizer, before_text, diff_text

def tokenize(text):
  return tokenizer.encode(text)

def tokenize_input(verbalizer, before_text):
  text = f'<s> [INST] {verbalizer} [/INST]\n{before_text}'
  print(text)
  return tokenizer(text, return_tensors='pt').to(device)


verbalizer, before_text, diff_text = get_dataset()

messages = [
    {
        "role": "system",
        "content": verbalizer,
    },
    {   "role": "user", 
        "content": before_text
    },
 ]

it = tokenizer.apply_chat_template(messages, tokenize=False)

tokenized_chat = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True, return_tensors="pt").to(device)

print("BEFORE TEXT: \n\n\n", tokenizer.decode(tokenized_chat[0]))

outputs = model.generate(tokenized_chat, max_new_tokens=4000)

print("--------------------\nOUTPUT\n\n", tokenizer.decode(outputs[0]))






