import os
import re
from tqdm import tqdm
import torch
from unsloth import FastLanguageModel
from dotenv import load_dotenv
from huggingface_hub import login
from datasets import load_dataset
from prompt import class_prompt

load_dotenv()

login(os.getenv("HUGGINGFACE_TOKEN"))


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
            print(predicted_label)
            predicted_label = "Invalid"
    
    return predicted_label


def load_classifier_model():
  model_name = "unsloth/Meta-Llama-3.1-8B-Instruct-bnb-4bit"

  model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=model_name,
    max_seq_length=4096,
    load_in_4bit=True,
    dtype=None
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


def main():
    results = []
    dataset = load_dataset("minnesotanlp/scholawrite_test")
    df = dataset["train"].to_pandas()

    classifier_model, classifier_tokenizer = load_classifier_model()

    with torch.no_grad():
        for before_text in tqdm(df["before text"].values):
            writing_intention = predict_intention(before_text, classifier_model, classifier_tokenizer)
            results.append(writing_intention)
    
    df["predicted"] = results
    df.to_csv("llama8_meta_class_result.csv", index=False)

if __name__ == "__main__":
  main()