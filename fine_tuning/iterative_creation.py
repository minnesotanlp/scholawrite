import os
import pandas as pd
import torch
from torch.distributed.fsdp import FullyShardedDataParallel as FSDP
from torch.distributed.fsdp import CPUOffload
import torch.distributed as dist
from torch import cuda, bfloat16
from transformers import AutoModelForCausalLM, TrainingArguments, AutoTokenizer, BitsAndBytesConfig, pipeline
from datasets import Dataset
from peft import LoraConfig, get_peft_model
import accelerate # not used in code but reuqired for device_map='auto'
from datasets import load_dataset
import datasets
from trl import SFTTrainer
import json
import random
from dotenv import load_dotenv
from pymongo import MongoClient

from transformers import AutoTokenizer, AutoModelForCausalLM

load_dotenv()

HF_TOKEN = os.environ["HUGGINGFACE_API_KEY"]

with open("labels_for_computation.json", 'r') as file:
    labels = json.load(file)

def load_tokenizer():
    tokenizer = AutoTokenizer.from_pretrained(
        "meta-llama/Meta-Llama-3-8B", 
        token = HF_TOKEN,
    )
    tokenizer.add_special_tokens({'pad_token': '<|end_of_text|>'})

    return tokenizer

def formatting_prompts_func(row):
    instruct_tune_template="""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are a writing assistant that can generate ideas, implement ideas, and revise paper for scholarly writing. The paper is written in LaTeX. The context of the Paper is provided below, paired with instruction that describes a writing task. Write a response that appropriately completes the request. Do not repeat any instructions. Do not output any instructions. You are not allowed to talk about yourself.<|eot_id|>
<|start_header_id|>user<|end_header_id|>

{BEFORE_TEXT}.

{VERBALIZER}.<|eot_id|>"""

    BEFORE_TEXT    = row["before_text"]
    INTENTION      = row["writing_intention"]
    VERBALIZER           = random.choice(labels[INTENTION]["verbalizer"])

    tune_ready_prompt = instruct_tune_template.format(
                        VERBALIZER = VERBALIZER,
                        BEFORE_TEXT = BEFORE_TEXT)
  
    return tune_ready_prompt
    #return {"tune" : tune_ready_prompts}

def format_input_text():
  row = {
     'before_text': "",
     'writing_intention': "Idea Generation",
  }

  return formatting_prompts_func(row)

def iterative_inference(tokenizer, model):
  start_text = format_input_text()
  input = tokenizer.encode(start_text)

  print(input)

  outputs = model.generate(input, max_new_tokens=5000, do_sample=True, top_k=50, top_p=0.95)

  print("output:", outputs)

def main():
  output_dir = "llama3_qlora"
  #tokenizer = AutoTokenizer.from_pretrained(output_dir)
  tokenizer = load_tokenizer()
  model = AutoModelForCausalLM.from_pretrained(output_dir, load_in_4bit=True, device_map="auto")

  iterative_inference(tokenizer, model)

if __name__ == "__main__":
    main()