import os
import json
from tqdm import tqdm
from dotenv import load_dotenv
load_dotenv()

import torch
from unsloth import FastLanguageModel
from huggingface_hub import login
login(os.getenv("HUGGINGFACE_TOKEN"))

from one_time_inference_prompt import one_time_inference_prompt


def setup():
    cwd = os.getcwd()

    folders = ["llama3_output"]
    
    for folder in folders:
        os.makedirs(os.path.join(cwd, folder), exist_ok = True)
        print(f"{folder} created!")


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


def writing_inference(seedname, before_text, model, tokenizer):
    text = one_time_inference_prompt(before_text)

    with open(f"./llama3_output/{seedname}_prompt.json", "w") as f:
        json.dump(text, f, indent=4)

    input_ids = tokenizer.apply_chat_template(text, max_length=4096, tokenize=True, add_generation_prompt=True, return_tensors="pt")

    outputs = model.generate(input_ids, max_new_tokens=len(before_text)+100, do_sample=True, top_k=50, top_p=0.95)

    response = tokenizer.batch_decode(outputs)

    with open(f"./llama3_output/{seedname}_log.txt", "w") as f:
        f.write(str(response))

    response = response[0].split("<|start_header_id|>assistant<|end_header_id|>")[1].strip()
    response = response.replace("<|eot_id|>", "")

    return response


def main():
    writing_model, writing_tokenizer = load_writing_inference_model()

    setup()

    seeds = ["seed1", "seed2", "seed3", "seed4"]

    for each in tqdm(seeds):
        with open(f"../seeds/{each}.txt", "r") as f:
            seed = f.read()

        with torch.no_grad():
            response = writing_inference(each, seed, writing_model, writing_tokenizer)

        with open(f"./llama3_output/{each}_result.txt", 'w') as file:
            file.write(response)


if __name__ == "__main__":
  main()