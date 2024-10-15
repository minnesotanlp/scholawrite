import os

from tqdm import tqdm
import torch
from unsloth import FastLanguageModel
from transformers import AutoModelForCausalLM, AutoTokenizer, LlamaForCausalLM
from peft import PeftModel
from datasets import Dataset
import pandas as pd
import random

from dataset_utils import add_special_tokens
from taxonomy import RELEVANT_CLASSES

output_dir = "iterative_inference_output_1"

def load_seed(fname=f"{output_dir}/seed.txt"):
  with open(fname, 'r') as file:
    content = file.read()

  return content

def load_classifier_model():
  model_name = "unsloth/Llama-3.2-1B-bnb-4bit"

  dataset_dir = "datasets/intention_test_dataset"
  model_dir = "scholawrite/results/unsloth/classifier/model_save"

  model = AutoModelForCausalLM.from_pretrained(model_name)
  tokenizer = AutoTokenizer.from_pretrained(model_name)

  add_special_tokens(tokenizer)

  model = PeftModel.from_pretrained(model, model_dir, ignore_mismatched_sizes=True)
  model.resize_token_embeddings(len(tokenizer))
  model.eval()
  model.to("cuda")

  return model, tokenizer

def load_writing_inference_model():
  model_name = "unsloth/Llama-3.2-1B-bnb-4bit"

  dataset_dir = "datasets/text_generation_test_dataset"
  model_dir = "results/unsloth/Llama-3.2-1B-bnb-4bit_run_2024-10-06 04:23:59.743722_intention_bt/checkpoint-17"

  model = AutoModelForCausalLM.from_pretrained(model_name)
  tokenizer = AutoTokenizer.from_pretrained(model_name)

  add_special_tokens(tokenizer)

  model = PeftModel.from_pretrained(model, model_dir, ignore_mismatched_sizes=True)
  model.resize_token_embeddings(len(tokenizer))
  model.eval()
  model.to("cuda")

  return model, tokenizer

def predict_intention(text, model, tokenizer):
  instruction_prompt = """Identify the most likely next writing intention of a graduate researcher when editing the following text.

  ### Input:
  {}

  ### Response:
  {}"""

  instruction = instruction_prompt.format(text, "") + tokenizer.eos_token

  tokenized_text = tokenizer(instruction, max_length=4096, padding=True, truncation=True, return_tensors="pt")

  input_ids = tokenized_text["input_ids"]
  attention_mask = tokenized_text["attention_mask"]

  outputs = model.generate(input_ids, attention_mask=attention_mask, max_new_tokens=10, do_sample=True, top_k=50, top_p=0.95)

  #response = tokenizer.batch_decode(outputs)[0].split("### Response:")[1].strip()
  response = tokenizer.batch_decode(outputs)

  print(response)
  raise Exception

  predicted_class="None"

  for cl in RELEVANT_CLASSES:
    if (response.startswith(cl)):
      predicted_class=cl
      break

  if (predicted_class == "None"):
    print("###########\npredicted class is NONE\n###############")
  return predicted_class

def writing_inference(before_text, model, tokenizer):
  prompt = """Given an excerpt from a research paper and a scholarly writing intention, revise or add to the text to fulfill this writing intention.

  ### Input:
  <INPUT><BT>{}</BT><WI>{}</WI></INPUT>

  ### Response:
  {}"""

  wi = random.choice(RELEVANT_CLASSES)

  EOS_TOKEN = tokenizer.eos_token
  instruction = prompt.format(before_text, wi,  "") + EOS_TOKEN


  tokenized_text = tokenizer(instruction, max_length=4096, padding=True, truncation=True, return_tensors="pt")

  input_ids = tokenized_text["input_ids"]
  attention_mask = tokenized_text["attention_mask"]

  outputs = model.generate(input_ids, attention_mask=attention_mask, max_new_tokens=100, do_sample=True, top_k=50, top_p=0.95)

  response = tokenizer.batch_decode(outputs)[0].split("### Response:")[1].strip()
  #response = tokenizer.batch_decode(outputs)

  return response

def get_random_paragraph(text):
  paragraphs = text.split('\n')
  random_paragraph = random.choice(paragraphs)

  index = paragraphs.index(random_paragraph)

  text_before = '\n'.join(paragraphs[:index])
  text_after = '\n'.join(paragraphs[index + 1:])
  
  return random_paragraph.strip(), text_before.strip(), text_after.strip()

def main():
  #classifier_model, classifier_tokenizer = load_classifier_model()
  writing_model, writing_tokenizer = load_writing_inference_model()

  current = load_seed()
  print(current)

  with torch.no_grad():
    for i in range(100):
      #current = predict_intention(current, classifier_model, classifier_tokenizer)

      para, bt, at = get_random_paragraph(current)

      output= writing_inference(para, writing_model, writing_tokenizer)

      print(output)

      current = bt + output + at

      with open(f"{output_dir}/iter_{i}.txt", "w") as file:
        file.write(current)



if __name__ == "__main__":
  main()