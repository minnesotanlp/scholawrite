import os

from tqdm import tqdm
import torch
from unsloth import FastLanguageModel

from prompt import text_gen_prompt, class_prompt

from dotenv import load_dotenv
load_dotenv()

from huggingface_hub import login
login(os.getenv("HUGGINGFACE_TOKEN"))

output_dir = "./llama_output/seed3"

generation_dir = f"{output_dir}/generation"
intention_dir = f"{output_dir}/intention"

os.makedirs(generation_dir, exist_ok=True)
os.makedirs(intention_dir, exist_ok=True)

def load_seed(fname):
  with open(fname, 'r') as file:
    content = file.read()
  return content


def process_label(model_output):
    all_labels = ['Text Production', 'Visual Formatting', 'Clarity', 'Section Planning',
 'Structural', 'Object Insertion', 'Cross-reference', 'Fluency',
 'Idea Generation', 'Idea Organization', 'Citation Integration', 'Coherence',
 'Linguistic Style', 'Scientific Accuracy', 'Macro Insertion']

 
    if model_output not in all_labels:
        found = 0
        for true_label in all_labels:
            if true_label in model_output:
                model_output = true_label
                found = 1
                break

        # If the output from gpt didn't contain any expeceted label
        if found != 1:
            model_output = "Text Production"
    
    return model_output


def load_classifier_model():
  model_name = "unsloth/Llama-3.2-3B-Instruct-bnb-4bit"

  model, tokenizer = FastLanguageModel.from_pretrained(
  model_name=model_name,
  max_seq_length=4096,
  load_in_4bit=True,
  dtype=None
  )

  FastLanguageModel.for_inference(model)

  return model, tokenizer


def load_writing_inference_model():
  model_name = "unsloth/Llama-3.2-3B-Instruct-bnb-4bit"

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


def main():
  classifier_model, classifier_tokenizer = load_classifier_model()
  writing_model, writing_tokenizer = load_writing_inference_model()

  current = load_seed("../seeds/seed3.txt")
  print(current)

  with torch.no_grad():
    for i in tqdm(range(100)):
      writing_intention = predict_intention(current, classifier_model, classifier_tokenizer)

      output= writing_inference(current, writing_intention, writing_model, writing_tokenizer)

      current = output

      with open(f"{generation_dir}/iter_generation_{i}.txt", "w") as file:
        file.write(output)

      with open(f"{intention_dir}/iter_intention_{i}.txt", "w") as file:
        file.write(writing_intention)
        

if __name__ == "__main__":
  main()