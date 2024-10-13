import re

from taxonomy import RELEVANT_CLASSES

def generate_train_template(before_text, label):
  data_prompt = f"Classify the latex text into one of the following writing intentions: {', '.join(str(x) for x in RELEVANT_CLASSES)} and return only the label as the answer. ### text: {before_text}"
  return [
    {"role": "user", "content": data_prompt},
    {"role": "assistant", "content": label}
  ]

def generate_test_prompt(before_text):
  data_prompt = f"Classify the latex text into one of the following writing intentions: {', '.join(str(x) for x in RELEVANT_CLASSES)} and return only the label as the answer. ### text: {before_text}"
  return [
    {"role": "user", "content": data_prompt}
  ]
