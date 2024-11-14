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
from prompt import text_gen_prompt, class_prompt, WRITING_INTENTIONS

seed = "seed4"

seed_txt = f"iterative_writing_eval_2/seeds/{seed}.txt"
output_dir = f"iterative_writing_eval_2/llama3_output/{seed}"

generation_dir = f"{output_dir}/generation"
intention_dir = f"{output_dir}/intention"

#os.makedirs(generation_dir, exist_ok=True)
#os.makedirs(intention_dir, exist_ok=True)

def load_seed(fname=seed_txt):
  with open(fname, 'r') as file:
    content = file.read()

  return content

def load_classifier_model():
  model_name = "unsloth/Llama-3.2-1B-bnb-4bit"

  model_dir = "results/unsloth/Llama-3.2-3B-bnb-4bit_run__CLASSIFIER_nov10/model_save"

  model, tokenizer = FastLanguageModel.from_pretrained(
  model_name=model_dir,
  max_seq_length=4096,
  load_in_4bit=True,
  dtype=None
  )

  FastLanguageModel.for_inference(model)

  return model, tokenizer

def load_writing_inference_model():
  model_name = "unsloth/Llama-3.2-1B-bnb-4bit"

  dataset_dir = "datasets/text_generation_test_dataset"
  #model_dir = "results/unsloth/Llama-3.2-3B-bnb-4bit_run_2024-10-15 04:04:14.619753_intention_bt/model_save"
  model_dir = "results/unsloth/Llama-3.2-3B-bnb-4bit_run__TEXT_PREDICTION/model_save"

  model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=model_dir,
    max_seq_length=4096,
    load_in_4bit=True,
    dtype=None,
  )
  FastLanguageModel.for_inference(model)

  return model, tokenizer

def predict_intention(text, model, tokenizer):
  text = class_prompt(text)
  input_ids = tokenizer.apply_chat_template(text, tokenize=True, add_generation_prompt=True, return_tensors="pt")

  #tokenized_text = tokenizer(instruction, max_length=4096, padding=True, truncation=True, return_tensors="pt")

  #input_ids = tokenized_text["input_ids"]
  #attention_mask = tokenized_text["attention_mask"]

  outputs = model.generate(input_ids, max_new_tokens=10, do_sample=True, top_k=50, top_p=0.95)

  #response = tokenizer.batch_decode(outputs)[0].split("### Response:")[1].strip()
  response = tokenizer.batch_decode(outputs)

  response = response[0].split("<|start_header_id|>assistant<|end_header_id|>")[1].strip()

  predicted_class="None"

  for cl in WRITING_INTENTIONS:
    if (response.startswith(cl)):
      predicted_class=cl
      print(cl)
      break

  print("\n\n")
  print("predicted class: ", predicted_class)
  print("\n\n")

  if (predicted_class not in WRITING_INTENTIONS or predicted_class == "Artifact"):
    predicted_class = "Text Production"

  return predicted_class

def writing_inference(before_text, writing_intention, model, tokenizer):
  #def generate_test_template(before_text, writing_intention):
  #  prompt = f"""Given an excerpt from a research paper and a scholarly writing intention, revise or add to the text to fulfill this writing intention. ### exerpt: {before_text} ### Writing intention: {writing_intention}"""
  #  return [
  #    {"role": "user", "content": prompt},
  #  ]

  text = text_gen_prompt(before_text, writing_intention)
  input_ids = tokenizer.apply_chat_template(text, max_length=4096, tokenize=True, add_generation_prompt=True, return_tensors="pt")

  outputs = model.generate(input_ids, max_new_tokens=len(before_text)+100, do_sample=True, top_k=50, top_p=0.95)

  response = tokenizer.batch_decode(outputs)

  #print("\n\n\n######################################")
  #print("ITER")
  #print(response)

  response = response[0].split("<|start_header_id|>assistant<|end_header_id|>")[1].strip()
  response = response.replace("<|eot_id|>", "")

  #print("\n\n\n", response)

  return response

def get_random_paragraph(text):
  paragraphs = text.split('\n')
  random_paragraph = random.choice(paragraphs)

  index = paragraphs.index(random_paragraph)

  text_before = '\n'.join(paragraphs[:index])
  text_after = '\n'.join(paragraphs[index + 1:])
  
  return random_paragraph.strip(), text_before.strip(), text_after.strip()

def main():
  classifier_model, classifier_tokenizer = load_classifier_model()
  writing_model, writing_tokenizer = load_writing_inference_model()

  current = load_seed()
  print(current)

  #prev_intention = None
  #actual_index = 0

  with torch.no_grad():
    for i in tqdm(range(100)):
      writing_intention = predict_intention(current, classifier_model, classifier_tokenizer)

      para, bt, at = get_random_paragraph(current)

      output= writing_inference(para, writing_intention, writing_model, writing_tokenizer)

      print(output)

      current = bt + output + at

      with open(f"{generation_dir}/iter_generation_{i}.txt", "w") as file:
        file.write(current)

      with open(f"{intention_dir}/iter_intention_{i}.txt", "w") as file:
        file.write(writing_intention)

if __name__ == "__main__":
  main()