"""
 Analysis of intentions during inference
"""

import os

import pandas as pd
from datasets import load_dataset
from huggingface_hub import login
from dotenv import load_dotenv
from unsloth import FastLanguageModel
from tqdm import tqdm

load_dotenv()
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
login(token=HUGGINGFACE_TOKEN)

full_ds = load_dataset("minnesotanlp/scholawrite", revision="anonymous_data")

ds = full_ds["train"]
df = pd.DataFrame(ds)

# Function to find future matches
def check_future_pairs(df):
    # Create a column to store the result for each row
    df['has_future_pair'] = False

    # Iterate over each row to find matches
    for idx, row in df.iterrows():
        # Filter future rows
        future_rows = df[df['timestamp'] > row['timestamp']]
        
        # Check if the current row's after_text exists as a before_text in future rows
        if row['after text'] in future_rows['before text'].values:
            df.at[idx, 'has_future_pair'] = True
    
    return df

#result_df = check_future_pairs(df)
#print(result_df["has_future_pair"].value_counts())
#raise Exception

#df["chain"] = df.apply(lambda x: [x["before text"], x["after text"]], axis=1)

def build_chains(df):
  df['chain'] = None
  df['used'] = False 

  for idx, row in tqdm(df.iterrows(), total=df.shape[0], desc="Building Chains", unit="row"):
    if df.at[idx, 'used']:
      continue
    
    current_chain = [[row['before text'], row['after text']]]
    df.at[idx, 'used'] = True 
    
    for next_idx, next_row in df[df['timestamp'] > row['timestamp']].iterrows():
      if df.at[next_idx, 'used']:
        continue
      
      if current_chain[-1][1] == next_row['before text']:
        current_chain.append([next_row['before text'], next_row['after text']])
        df.at[next_idx, 'used'] = True
        found_match = True
        break

    df.at[idx, 'chain'] = current_chain

  df = df[df['used']]
  df = df.drop(columns=['used'])

  return df

result_df = build_chains(df)
print(result_df)

