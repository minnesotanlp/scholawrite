import os
import re
from tqdm import tqdm
import torch
from unsloth import FastLanguageModel
from dotenv import load_dotenv
from huggingface_hub import login

from prompt import text_gen_prompt, class_prompt

load_dotenv()

login(os.getenv("HUGGINGFACE_TOKEN"))

output_folder_name = "llama8_DEC8_output"

def setup(seed_name):
  global generation_dir, intention_dir, generation_raw_dir, intention_raw_dir, path_to_seed

  output_dir = os.path.join(f"../../{output_folder_name}", seed_name)

  generation_dir = f"{output_dir}/generation"
  intention_dir = f"{output_dir}/intention"

  generation_raw_dir = f"{output_dir}/generation_raw"
  intention_raw_dir = f"{output_dir}/intention_raw"

  os.makedirs(generation_dir, exist_ok=True)
  os.makedirs(intention_dir, exist_ok=True)

  os.makedirs(generation_raw_dir, exist_ok=True)
  os.makedirs(intention_raw_dir, exist_ok=True)

  path_to_seed = os.path.join("../../seeds", f"{seed_name}.txt")

def load_seed(fname):
  with open(fname, 'r') as file:
    content = file.read()
  return content


def process_label(predicted_label):
    all_labels = ['Text Production', 'Visual Formatting', 'Clarity', 'Section Planning',
 'Structural', 'Object Insertion', 'Cross-reference', 'Fluency',
 'Idea Generation', 'Idea Organization', 'Citation Integration', 'Coherence',
 'Linguistic Style', 'Scientific Accuracy', 'Macro Insertion']

 
    if predicted_label not in all_labels:
        found = 0
        for true_label in all_labels:
            if true_label in predicted_label:
                predicted_label = true_label
                found = 1
                break
        
        # If the output from gpt didn't contain any expeceted label
        if found != 1:
            predicted_label = "Text Production"
    
    return predicted_label


def load_classifier_model():
  model_name = "minnesotanlp/scholawrite-llama3.1-8b-classifier"

  model, tokenizer = FastLanguageModel.from_pretrained(
  model_name=model_name,
  max_seq_length=4096,
  load_in_4bit=True,
  dtype=None
  )

  FastLanguageModel.for_inference(model)

  return model, tokenizer


def load_writing_inference_model():
  model_name = "/users/1/wang9257/scholawrite/results/unsloth/Llama-3.1-8B-bnb-4bit_run__LLAMA_8B_WRITING_DEC_8/model_save"

  model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=model_name,
    max_seq_length=4096,
    load_in_4bit=True,
    dtype=None,
  )
  FastLanguageModel.for_inference(model)

  return model, tokenizer


def predict_intention(text, model, tokenizer):
  text = class_prompt(text)
  input_ids = tokenizer.apply_chat_template(text, tokenize=True, add_generation_prompt=True, return_tensors="pt")

  outputs = model.generate(input_ids, max_new_tokens=100, do_sample=True, top_k=50, top_p=0.95)

  response = tokenizer.batch_decode(outputs)

  response = response[0].split("<|start_header_id|>assistant<|end_header_id|>")[1].strip()

  predicted_class= process_label(response)

  return predicted_class


def writing_inference(before_text, writing_intention, model, tokenizer):
  text = text_gen_prompt(before_text, writing_intention)
  input_ids = tokenizer.apply_chat_template(text, max_length=4096, tokenize=True, add_generation_prompt=True, return_tensors="pt")

  outputs = model.generate(input_ids, max_new_tokens=len(before_text)+100, do_sample=True, top_k=50, top_p=0.95)

  response = tokenizer.batch_decode(outputs)

  response = response[0].split("<|start_header_id|>assistant<|end_header_id|>")[1].strip()
  response = response.replace("<|eot_id|>", "")

  return response


def clean_text(text):
    text = re.sub(r"<del>.*?<\/del>", "", text, flags=re.DOTALL)

    text = re.sub(r"<same>(.*?)<\/same>", r"\1", text, flags=re.DOTALL)

    text = re.sub(r"<add>(.*?)<\/add>", r"\1", text, flags=re.DOTALL)

    tags_to_remove = ["<add>", "</add>", "<del>", "</del>", "<same>", "</same>"]
    for tag in tags_to_remove:
        text = text.replace(tag, "")
    
    return text

def save_raw_output(output, writing_intention, i):
  with open(f"{generation_raw_dir}/iter_generation_{i}.txt", "w") as file:
    file.write(output)

  with open(f"{intention_raw_dir}/iter_intention_{i}.txt", "w") as file:
    file.write(writing_intention)


def aggregate_iterative_writing():
  prev_writing = load_seed(path_to_seed)
  pbar = tqdm(total=100)

  with torch.no_grad():
    i = 0
    j = 0 # j represent the true number of iteration, which regardless intentions
    while i < 100:
      writing_intention = predict_intention(prev_writing, classifier_model, classifier_tokenizer)

      output = writing_inference(prev_writing, writing_intention, writing_model, writing_tokenizer)

      # save the intermediate output in case this intention is same as previous
      save_raw_output(output, writing_intention, j)

      # if this is the model's first output, we don't compare.
      # We setup the previous intention and writing for comparison in future iterations
      if j == 0 :
        prev_intention = writing_intention
        prev_writing = clean_text(output)

      # if current writing intetion is same as previous,
      # we let the model revise it again in the same iteration (i).
      elif writing_intention == prev_intention:
        prev_writing = clean_text(output)

      # if current writing intetion is NOT same as previous,
      # we save the model's aggreated writing to the file.
      # Then move on to next iteration
      else:
        with open(f"{generation_dir}/iter_generation_{i}.txt", "w") as file:
          file.write(prev_writing)

        with open(f"{intention_dir}/iter_intention_{i}.txt", "w") as file:
          file.write(prev_intention)
        
        prev_writing = clean_text(output)
        prev_intention = writing_intention

        i += 1
        pbar.update(1)

      j += 1

def iterative_writing():
  prev_intention = ""
  prev_writing = load_seed(path_to_seed)

  with torch.no_grad():
    for i in tqdm(range(100)):
        writing_intention = predict_intention(prev_writing, classifier_model, classifier_tokenizer)

        output = writing_inference(prev_writing, writing_intention, writing_model, writing_tokenizer)

        save_raw_output(output, writing_intention)

        prev_writing = clean_text(output)

        with open(f"{generation_dir}/iter_generation_{i}.txt", "w") as file:
          file.write(prev_writing)

        with open(f"{intention_dir}/iter_intention_{i}.txt", "w") as file:
          file.write(writing_intention)


def main():
  global classifier_model, classifier_tokenizer, writing_model, writing_tokenizer
  classifier_model, classifier_tokenizer = load_classifier_model()
  writing_model, writing_tokenizer = load_writing_inference_model()

  for each in ["seed1", "seed2", "seed3", "seed4"]:
    print(f"Working on {each}")
    setup(each)
    aggregate_iterative_writing()
    print("-"*100)


if __name__ == "__main__":
  main()