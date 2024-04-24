import os
import pandas as pd
from dotenv import load_dotenv
import transformers
from transformers import AutoModelForCausalLM, AutoTokenizer
import pymongo
from pymongo import MongoClient
import matplotlib.pyplot as plt
import numpy as np

load_dotenv()

hf_api_key = os.environ["HUGGINGFACE_API_KEY"]

device = "cuda" # the device to load the model onto

model = AutoModelForCausalLM.from_pretrained("mistralai/Mistral-7B-Instruct-v0.1", token=hf_api_key)
model.eval()

tokenizer = AutoTokenizer.from_pretrained("mistralai/Mistral-7B-Instruct-v0.1", token=hf_api_key)

client = MongoClient('localhost', 5001)

db = client.dataset_db
annotation = db.fine_tuning

query = {}

cursor = annotation.find(query)

activity_df = pd.DataFrame(list(cursor))

activity_df

before_text = activity_df.iloc[0]["before_text"]
after_text = activity_df.iloc[0]["after_text"]
print(before_text)

generate_text = transformers.pipeline(
    model=model, tokenizer=tokenizer,
    return_full_text=False,  # if using langchain set True
    task="text-generation",
    # we pass model parameters here too
    temperature=0.1,  # 'randomness' of outputs, 0.0 is the min and 1.0 the max
    top_p=0.15,  # select from top tokens whose probability add up to 15%
    top_k=0,  # select from top 0 tokens (because zero, relies on top_p)
    max_new_tokens=4000,  # max number of tokens to generate in the output
    repetition_penalty=1.1,  # if output begins repeating increase
    device=device
)

res = generate_text(before_text)
print(res[0]["generated_text"])

print(res)