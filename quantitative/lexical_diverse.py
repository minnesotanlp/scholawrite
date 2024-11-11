import os
from pylatexenc.latex2text import LatexNodes2Text
import nltk

from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

nltk.download('punkt')
nltk.download('stopwords')
stop_words = set(stopwords.words('english'))

def calculate_lexical_diverse(text):

    text = LatexNodes2Text().latex_to_text(text)
    tokens = word_tokenize(text)

    print(text)
    print(tokens)

    new_tokens = []
    for word in tokens:
        if word.isalnum() and (word not in stop_words):
            new_tokens.append(word.lower())

    print(new_tokens)
    result = len(set(new_tokens)) / len(new_tokens)
    print(result)

    return result

# abs_path = input("Please enter the abs path to folder:")
# outputs = ["llama3_outpt", "llama8_output"]
# all_seeds = ["seed1", "seed2", "seed3", "seed4"]
# all_output = {}

# for output in outputs:
#     all_output[output] = {}
#     for seed in all_seeds:
#         path_to_folder = os.path.join(abs_path, output, seed, "generation/iter_generation_99.txt")
#         with open(path_to_folder) as file:
#             text = file.read()
#             all_output[output][seed] = calculate_lexical_diverse(text)
# print(all_output)


text=""
with open("./iter_generation_99.txt") as file:
    text = file.read()

calculate_lexical_diverse(text)