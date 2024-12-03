import os
from dotenv import load_dotenv
load_dotenv()

from langchain_core.prompts import load_prompt
import openai

from iterative_writing_cls_and_gen.definitions import definition_persona

openai.api_key = os.getenv('OPEN_AI_API')

classification_system_prompt = load_prompt("./iterative_writing_cls_and_gen/classification_templates/system.yaml")
classification_user_prompt = load_prompt("./iterative_writing_cls_and_gen/classification_templates/user.yaml")

generation_system_prompt = load_prompt("./iterative_writing_cls_and_gen/generation_templates/persona_system.yaml")
generation_user_prompt = load_prompt("./iterative_writing_cls_and_gen/generation_templates/user.yaml")

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
label = "Cross-reference"

text_token_len = len(enc.encode(classification_test['before_text'].iloc[longest_string])) * 100
label_token_len = len(enc.encode("Cross-reference")) * 100

csp = len(enc.encode(classification_system_prompt.template)) * 100
cup = len(enc.encode(classification_user_prompt.format(before_text=text))) * 100
gsp = len(enc.encode(generation_system_prompt.format(persona_definition=definition_persona["Cross-reference"]))) * 100
gup = len(enc.encode(generation_user_prompt.format(before_text=text))) * 100


input_price = (csp + cup + gsp + gup)/1000000 * 2.5
output_price = (text_token_len + label_token_len)/1000000 * 10

print(input_price + output_price)