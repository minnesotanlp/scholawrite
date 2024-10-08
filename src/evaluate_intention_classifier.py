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

dataset_dir = "datasets/intention_test_dataset"
model_dir = "results/unsloth/Llama-3.2-1B-bnb-4bit_run_2024-10-06 04:23:59.743722_intention_bt/checkpoint-17"
#model_dir = "results/unsloth/Llama-3.2-1B-bnb-4bit_run_2024-10-06 04:27:15.452895_intention_bt/model_save" 

model = AutoModelForCausalLM.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)

add_special_tokens(tokenizer)

model = PeftModel.from_pretrained(model, model_dir, ignore_mismatched_sizes=True)

model.to("cuda")

def preprocess_function(instructions):
  return tokenizer(instructions['text'], truncation=True, padding=True, max_length=4096, return_tensors="pt")

ds = Dataset.load_from_disk(dataset_dir)
ds = ds.map(preprocess_function, batched=True)
ds.set_format(type='torch', columns=["input_ids", "attention_mask", "label"])

model.resize_token_embeddings(len(tokenizer))

model.eval()

evaluation_save = []

with torch.no_grad():
  for row in tqdm(ds):
    inputs = row["input_ids"].unsqueeze(0)
    attention_mask = row["attention_mask"].unsqueeze(0)

    #output = model.generate(row, max_new_tokens = 100)
    outputs = model.generate(inputs, attention_mask=attention_mask, max_new_tokens=10, do_sample=True, top_k=50, top_p=0.95)

    # split("### Response:").strip()[1]
    response = tokenizer.batch_decode(outputs)[0].split("### Response:")[1].strip()

    predicted_class="None"

    for cl in RELEVANT_CLASSES:
      if (response.startswith(cl)):
        predicted_class=cl
        break
    
    evaluation_save.append([row["label"], predicted_class])
  
df = pd.DataFrame(evaluation_save, columns=["label", "predicted_label"])

df.to_csv("intention_class_eval.csv")
