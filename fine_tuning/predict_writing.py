import os
import pandas as pd
from dotenv import load_dotenv
import transformers
from transformers import LongformerConfig, LongformerForSequenceClassification, LongformerTokenizerFast
import pymongo
from pymongo import MongoClient
import matplotlib.pyplot as plt
import numpy as np
from sklearn.model_selection import train_test_split


load_dotenv()

MAX_LENGTH = 4096

config = LongformerConfig()

def get_data():
  client = MongoClient('localhost', 5001)

  db = client.dataset_db
  annotation = db.fine_tuning

  query = {}

  cursor = annotation.find(query)

  activity_df = pd.DataFrame(list(cursor))[["before_text", "writing_intention"]]
  return activity_df

def tokenize(batch):
  return tokenizer(batch["before_text"], padding = 'max_length', truncation=True, max_length = MAX_LENGTH)

model = LongformerForSequenceClassification.from_pretrained(
  'allenai/longformer-base-4096', 
  gradient_checkpointing=False, 
  attention_window = 512)

tokenizer = LongformerTokenizerFast.from_pretrained('allenai/longformer-base-4096', max_length = MAX_LENGTH)

print(get_data())



