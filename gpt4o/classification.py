import os
from dotenv import load_dotenv
load_dotenv()

from prompt import class_prompt
from datasets import load_dataset

import openai
openai.api_key = os.getenv('OPEN_AI_API')

import json
from tqdm import tqdm

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
    
    return predicted_label


def get_label(before_text):
    prompt = class_prompt(before_text)

    # call chatgpt
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=prompt
    )

    # rereieve chatgpt response and return to caller
    generated_response = response.choices[0].message.content
    predicted_class = process_label(generated_response)

    return predicted_class


def main():
  results = []
  dataset = load_dataset("minnesotanlp/scholawrite_test")
  df = dataset["train"].to_pandas()

  for before_text in tqdm(df["before text"].values):
    writing_intention = get_label(before_text)
    results.append(writing_intention)
  
  df["predicted"] = results
  df.to_csv("gpt4o_class_result.csv", index=False)


if __name__ == "__main__":
  main()