from tqdm import tqdm
import torch
from unsloth import FastLanguageModel
from transformers import AutoModelForCausalLM, AutoTokenizer, LlamaForCausalLM
from peft import PeftModel
from datasets import Dataset
import pandas as pd

from dataset_utils import add_special_tokens
from taxonomy import RELEVANT_CLASSES

model_name = "unsloth/Llama-3.2-1B-bnb-4bit"

dataset_dir = "datasets/text_generation_test_dataset"
model_dir = "results/unsloth/Llama-3.2-1B-bnb-4bit_run_2024-10-06 04:23:59.743722_intention_bt/checkpoint-17"

model = AutoModelForCausalLM.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)

add_special_tokens(tokenizer)

model = PeftModel.from_pretrained(model, model_dir, ignore_mismatched_sizes=True)

model.to("cuda")

def preprocess_function(instructions):
  return tokenizer(instructions['text'], truncation=True, padding=True, max_length=4096, return_tensors="pt")

ds = Dataset.load_from_disk(dataset_dir)
ds = ds.map(preprocess_function, batched=True)
ds.set_format(type='torch', columns=["input_ids", "attention_mask", "after_text"])

model.resize_token_embeddings(len(tokenizer))

model.eval()

with torch.no_grad():
  for row in tqdm(ds):
    inputs = row["input_ids"].unsqueeze(0)
    attention_mask = row["attention_mask"].unsqueeze(0)

    outputs = model.generate(inputs, attention_mask=attention_mask, max_new_tokens=10, do_sample=True, top_k=50, top_p=0.95)

    #response = tokenizer.batch_decode(outputs)[0].split("### Response:")[1].strip()
    response = tokenizer.batch_decode(outputs)

    print(response)
    raise Exception
