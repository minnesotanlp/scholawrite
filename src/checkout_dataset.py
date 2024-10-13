from datasets import load_dataset
dataset = load_dataset("charanhu/kannada-instruct-dataset-390-k", split="train")
from unsloth.chat_templates import standardize_sharegpt
dataset = standardize_sharegpt(dataset)

print(dataset)
