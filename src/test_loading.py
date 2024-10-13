from tqdm import tqdm
import torch
from unsloth import FastLanguageModel
from transformers import AutoModelForCausalLM, AutoTokenizer, LlamaForCausalLM
from peft import PeftModel
from datasets import Dataset, load_dataset
import pandas as pd

from dataset_utils import add_special_tokens
from taxonomy import RELEVANT_CLASSES
from classification_utils import generate_test_prompt

model_name = "unsloth/Llama-3.2-3B-bnb-4bit"

dataset_dir = "datasets/intention_test_dataset"
model_dir = "results/unsloth/classifier/model_save"

model, tokenizer = FastLanguageModel.from_pretrained(
  model_name=model_dir,
  max_seq_length=4096,
  load_in_4bit=True,
  dtype=None,
)

#data_prompt = """Identify the most likely next writing intention of a graduate researcher when editing the following text.
#
#### Input:
#{}
#
#### Response:
#{}"""

full_ds = load_dataset("minnesotanlp/scholawrite")
ds = full_ds["train"].select(range(100))

model.eval()
FastLanguageModel.for_inference(model)

evaluation_save = []

with torch.no_grad():
  for row in tqdm(ds):
    text = generate_test_prompt(row["before_text"])
    text = tokenizer.apply_chat_template(text, tokenize=True, add_generation_prompt=True, return_tensors="pt")

    print("text", text)

    #output = model.generate(row, max_new_tokens = 100)
    outputs = model.generate(text, max_new_tokens=15, do_sample=True, top_k=50, top_p=0.95)

    # split("### Response:").strip()[1]
    #response = tokenizer.batch_decode(outputs)[0].split("### Response:")[1].strip()
    response = tokenizer.batch_decode(outputs)
    response = response[0].split("<|start_header_id|>assistant<|end_header_id|>")[1].strip()

    predicted_class="None"

    for cl in RELEVANT_CLASSES:
      if (response.startswith(cl)):
        predicted_class=cl
        print(cl)
        break

    print("\n\n")
    print("response: ", response)
    print("predicted class: ", predicted_class)
    print("true class: ", row["label"])
    print("\n\n")
    print(predicted_class == row["label"])
    evaluation_save.append([row["label"], predicted_class])
  
df = pd.DataFrame(evaluation_save, columns=["label", "predicted_label"])

df.to_csv("intention_class_eval.csv")
