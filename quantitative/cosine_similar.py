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
from sentence_transformers import SentenceTransformer
import nltk

nltk.download('punkt')


def load_llama():
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name="unsloth/Llama-3.2-3B-Instruct-bnb-4bit",
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
    abs_path = "/workspace/iterative_writing_eval_2"
    outputs = ["llama3_output", "llama8_output"]
    all_seeds = ["seed1", "seed2", "seed3"]
    all_output = {}

    for output in outputs:
        all_output[output] = {}
        for seed in tqdm(all_seeds):
            path_to_seed = os.path.join(abs_path, "seeds", f"{seed}.txt")
            path_to_folder = os.path.join(abs_path, output, seed, "generation/iter_generation_99.txt")

            with open(path_to_seed) as file:
                seed_text = file.read()

            with open(path_to_folder) as file:
                text = file.read()

            all_output[output][seed] = get_similar_llama(seed_text, text, model, tokenizer)

    print(all_output)


if __name__ == "__main__":
    main()