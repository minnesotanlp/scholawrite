import os
from dotenv import load_dotenv
load_dotenv()

from prompt import text_gen_prompt, class_prompt
import openai

openai.api_key = os.getenv('OPEN_AI_API')


import json

ChatCompletions = []

import pandas as pd

import tiktoken
enc = tiktoken.encoding_for_model("gpt-4o")

from datasets import load_dataset

classification_test = load_dataset('minnesotanlp/scholawrite', 
                      revision='main')["test"].to_pandas()

longest_string = classification_test['before_text'].str.len().idxmax()
text = classification_test['before_text'].iloc[longest_string]

long_definition_label = "Coherence"
long_name_label = "Cross-reference"

# class_prompt return [{{"role": "user", "content": user_prompt}}], so use [0]["content"] to access the content
generation_input = len(enc.encode(class_prompt(text)[0]["content"])) * 100
classification_input = len(enc.encode(text_gen_prompt(text, long_definition_label)[0]["content"])) * 100

generation_output = len(enc.encode(text)) * 100
classification_output = len(enc.encode(long_name_label)) * 100


input_price = (generation_input + classification_input)/1000000 * 2.5
output_price = (generation_output + classification_output)/1000000 * 10

print(input_price + output_price)