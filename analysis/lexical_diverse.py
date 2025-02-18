import os
from transformers import AutoTokenizer

def calculate_lexical_diverse(text, tokenizer):

    encoded_text = tokenizer.encode(text)

    result = round(len(set(encoded_text)) / len(encoded_text), 4)

    return result


def main():
    abs_path = "../outputs"
    outputs = ["llama8_meta_output", "llama8_SW_output","gpt4o_output"]
    all_seeds = ["seed1", "seed2", "seed3", "seed4"]
    all_output = {}

    tokenizer = AutoTokenizer.from_pretrained("unsloth/Meta-Llama-3.1-8B-Instruct-bnb-4bit")

    for output in outputs:
        all_output[output] = {}
        for seed in all_seeds:
            try:
                path_to_folder = os.path.join(abs_path, output, seed, "generation/iter_generation_99.txt")
                with open(path_to_folder) as file:
                    text = file.read()
                    all_output[output][seed] = calculate_lexical_diverse(text, tokenizer)
            except:
                continue

    print(all_output)


if __name__ == "__main__":
    main()
