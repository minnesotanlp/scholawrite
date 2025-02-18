import os
from tqdm import tqdm
import accelerate
from dotenv import load_dotenv
from huggingface_hub import login
from unsloth import FastLanguageModel
import torch
from torch.nn.functional import cosine_similarity
from transformers import pipeline
import numpy as np


def load_llama():
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name="unsloth/Meta-Llama-3.1-8B-Instruct-bnb-4bit",
        max_seq_length=4096,
        load_in_4bit=True,
        dtype=None,
    )

    return model, tokenizer

def get_similar_llama(text1, text2, model, tokenizer):
    pipl = pipeline('feature-extraction', model=model, tokenizer=tokenizer)
    data = pipl(text1)
    data1 = torch.tensor(data)

    data = pipl(text2)
    data2 = torch.tensor(data)

    sentence_embedding1 = data1.mean(dim=1)
    sentence_embedding2 = data2.mean(dim=1)

    result = cosine_similarity(sentence_embedding1, sentence_embedding2, dim=1)

    return result


def main():
    model, tokenizer = load_llama()
    seed_path = "../seeds"
    output_abs_path = "../outputs"
    outputs = ["llama8_meta_output", "llama8_SW_output", "gpt4o_output"]
    all_seeds = ["seed1", "seed2", "seed3", "seed4"]
    all_output = {}

    for output in outputs:
        all_output[output] = {}
        for seed in tqdm(all_seeds):
            try:
                path_to_seed = os.path.join(seed_path, f"{seed}.txt")
                path_to_folder = os.path.join(output_abs_path, output, seed, "generation/iter_generation_99.txt")

                with open(path_to_seed) as file:
                    seed_text = file.read()

                with open(path_to_folder) as file:
                    final_text = file.read()

                all_output[output][seed] = get_similar_llama(seed_text, final_text, model, tokenizer)
            except:
                continue

    print(all_output)


if __name__ == "__main__":
    main()