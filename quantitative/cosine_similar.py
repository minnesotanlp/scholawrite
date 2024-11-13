import os

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


def load_sbert():
    model = SentenceTransformer("all-mpnet-base-v2")

    return model

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


def use_sent_transformer_entire(text1, text2, model):

    embedding1 = model.encode(text1)
    embedding2 = model.encode(text2)
    result = model.similarity(embedding1, embedding2)

    return result


def use_sent_transformer_token(text1, text2, model):

    sentences1 = nltk.sent_tokenize(text1)
    embeddings1 = model.encode(sentences1)

    sentences2 = nltk.sent_tokenize(text2)
    embeddings2 = model.encode(sentences2)

    similarities = model.similarity(embeddings1, embeddings2)

    result = similarities.mean()

    return result


sentence1 = """Never underestimate the willingness of the greedy to throw you under the bus. 
It's much more difficult to play tennis with a bowling ball than it is to bowl with a tennis ball. 
Best friends are like old tomatoes and shoelaces."""

sentence2 = """Never underestimate the willingness of the greedy to throw you under the bus. 
It's much more difficult to play tennis with a bowling ball than it is to bowl with a tennis ball."""


'''
Now we have two approach

approach1
sen1[0] - sen2[0]
sen1[0] - sen2[1]
sen1[1] - sen2[0]
sen1[1] - sen2[1]
sen3[2] - sen2[0]
sen3[2] - sen2[1]
we calculate a mean from this

approach2
get vector1 which is mean of sen1[0], sen1[1], sen1[2] vector
get vector2 which is mean of sen2[0], sen2[1] vector
consine-smiliarity between these vector1 and vector2

approach3
encode sen1 and sen2 into two vector
consine-smiliarity between these two
'''


def main():
    model, tokenizer = load_llama()
    abs_path = "/workspace/iterative_writing_eval_2"
    outputs = ["llama3_output", "llama8_output"]
    all_seeds = ["seed1", "seed2", "seed3"]
    all_output = {}

    for output in outputs:
        all_output[output] = {}
        for seed in all_seeds:
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