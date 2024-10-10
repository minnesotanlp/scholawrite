from datasets import load_from_disk

from langchain_core.prompts import load_prompt
import os
import pandas as pd

system_prompt = load_prompt("classification_templates/system.yaml")
user_prompt = load_prompt("classification_templates/user.yaml")

import tiktoken
enc = tiktoken.encoding_for_model("gpt-4o")

total_input_token = 0
total_output_token = 0
system_prompt_token = len(enc.encode(system_prompt.template))

dataset = load_from_disk("../datasets/intention_test_dataset")
df = dataset.to_pandas()

for each in df.iterrows():
    user_prompt_token = len(enc.encode(user_prompt.format(before_text = each[1]["before_text"])))
    total_input_token += user_prompt_token + system_prompt_token
    total_output_token += len(enc.encode(each[1]["label"]))

input_cost = (total_input_token / 1000000) * 2.5
output_cost = (total_output_token / 1000000) * 10
print("Input cost:", input_cost)
print("Output cost:", output_cost)
print("Total cost:", input_cost + output_cost)

