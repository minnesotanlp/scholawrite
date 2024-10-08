from datasets import load_from_disk

from langchain_core.prompts import load_prompt
import os
import pandas as pd

system_prompt = load_prompt("generation_prompts/system.yaml")
user_prompt = load_prompt("generation_prompts/user.yaml")

import tiktoken
enc = tiktoken.encoding_for_model("gpt-4o")

total_input_token = 0
total_output_token = 0
system_prompt_token = len(enc.encode(system_prompt.template))

dataset = load_from_disk("../datasets/intention_test_dataset")
df = dataset.to_pandas()

# Assume the input text length and output text length is the average number of tokens in before_text column
sum = 0
for row in df.iterrows():
    try:
        sum += len(enc.encode(row[1]["before_text"]))
    except:
        pass
        
average_tokens = sum / len(df.index)

for i in range(100):
    user_prompt_token = average_tokens
    total_input_token += user_prompt_token + system_prompt_token
    total_output_token += average_tokens

input_cost = (total_input_token / 1000000) * 2.5
output_cost = (total_output_token / 1000000) * 10
print("Input cost:", input_cost)
print("Output cost:", output_cost)
print("Total cost:", input_cost + output_cost)
