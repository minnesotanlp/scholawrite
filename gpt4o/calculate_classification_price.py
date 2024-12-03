from datasets import load_dataset

from prompt import class_prompt
import os
import pandas as pd

import tiktoken
enc = tiktoken.encoding_for_model("gpt-4o")

total_input_token = 0
total_output_token = 0

dataset = load_dataset("minnesotanlp/scholawrite_test")
df = dataset["train"].to_pandas()


for each in df.iterrows():
    user_prompt_token = len(enc.encode(class_prompt(each[1]["before text"])[0]["content"]))
    total_input_token += user_prompt_token
    total_output_token += len(enc.encode(each[1]["label"]))

input_cost = (total_input_token / 1000000) * 2.5
output_cost = (total_output_token / 1000000) * 10
print("Input cost:", input_cost)
print("Output cost:", output_cost)
print("Total cost:", input_cost + output_cost)

