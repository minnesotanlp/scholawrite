from tqdm import tqdm
import torch
from unsloth import FastLanguageModel
from transformers import AutoModelForCausalLM, AutoTokenizer, LlamaForCausalLM
from peft import PeftModel
from datasets import Dataset, load_dataset
import pandas as pd

from dataset_utils import add_special_tokens
from prompt import class_prompt

model_name = "unsloth/Llama-3.2-1B-bnb-4bit"

dataset_dir = "datasets/intention_test_dataset"
model_dir = "results/unsloth/Llama-3.2-3B-bnb-4bit_run__CLASSIFICATION_NEW_LABEL_2/model_save"

model, tokenizer = FastLanguageModel.from_pretrained(
  model_name=model_dir,
  max_seq_length=4096,
  load_in_4bit=True,
  dtype=None,
)
FastLanguageModel.for_inference(model)

def formatting_prompt(examples):
  inputs       = examples["before text"]
  outputs      = examples["label"]
  input_ids = []
  labels = []
  attention_masks = []

  for input_, output_ in zip(inputs, outputs):
    text = class_prompt(input_)
    formatted_prompt = tokenizer.apply_chat_template(text, tokenize=False, add_generation_prompt=True)
    input_dict = tokenizer(formatted_prompt, return_tensors="pt", padding=True)
    input_ids.append(input_dict["input_ids"])
    attention_masks.append(input_dict["attention_mask"])
    labels.append(f"{output_}")
  return { "input_ids" : input_ids, "attention_mask": attention_masks, "label": labels}

#ds = load_dataset("minnesotanlp/scholawrite", revision="anonymous_data")["test"]
ds = load_dataset("minnesotanlp/scholawrite", revision="anonymous_data", split="test[0:50]")
ds = ds.map(formatting_prompt, batched=True)
ds.set_format(type='torch', columns=["input_ids", "attention_mask", "label"])

RELEVANT_CLASSES = set(ds["label"])

model.resize_token_embeddings(len(tokenizer))

model.eval()

evaluation_save = []

with torch.no_grad():
  #for row in tqdm(ds):
  for i, row in enumerate(ds):
    inputs = row["input_ids"]
    attention_mask = row["attention_mask"]

    #output = model.generate(row, max_new_tokens = 100)
    outputs = model.generate(inputs, attention_mask=attention_mask, max_new_tokens=35, do_sample=True, top_k=50, top_p=0.95, pad_token_id=tokenizer.eos_token_id)

    # split("### Response:").strip()[1]
    #response = tokenizer.batch_decode(outputs)[0].split("### Response:")[1].strip()
    response = tokenizer.batch_decode(outputs)
    response = response[0].split("<|start_header_id|>assistant<|end_header_id|>")[1].strip()

    #print(response, row["label"])
    print("###########")
    print("TRUE: ", row["label"])
    print("-----------")
    print("PRED:", response)
    print("###########")
    continue

    predicted_class="None"

    for cl in RELEVANT_CLASSES:
      if (response.startswith(cl)):
        predicted_class=cl
        break
    
    print(predicted_class == row["label"])
    evaluation_save.append([row["label"], predicted_class])
  
df = pd.DataFrame(evaluation_save, columns=["label", "predicted_label"])

df.to_csv("intention_class_eval.csv")
