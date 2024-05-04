import os
try:
    import transformers
    import torch
    import json
    import datetime
    import random
    from tqdm import tqdm
    from pymongo import MongoClient
except ImportError:
    os.system("pip install --no-cache-dir -r requirements.txt")


client = MongoClient("localhost", 5001)
db = client.flask_db
annotation = db.annotation
project_id = "656a440644dec9f71f2dee44"

valueToLabel = {
    "1": "Idea Generation", "2": "Idea Organization", "3": "Discourse Planning",
    "4": "Drafting", "5": "Lexical Chaining", "6": "Object Insertion",
    "7": "Semantic", "8": "Syntactic", "9": "Lexical",
    "10": "Structural", "11": "Visual", "12": "Quantitative",
    "13": "Feedback", "0": "No Label", "14": "Artifact", "15": "Command Insertion",
    "16": "Citation", "17": "Custom label"
}

annotator = annotation.find_one({"annotatorEmail": "lee03533@umn.edu"})
values = annotator[project_id]["filledArray"]


intentions = []
for k in range(len(values) - 1):
        if values[k] != values[k + 1]:
            for value in values[k]:
                  if value in valueToLabel and value != "14" and value != 0 and value != "0":
                        if intentions[-1:] != [valueToLabel[value]]:
                            intentions.append(valueToLabel[value])
for value in values[k]:
        if value in valueToLabel and value != "14" and value != 0 and value != "0":
            if intentions[-1:] != [valueToLabel[value]]:
                intentions.append(valueToLabel[value])


with open("intentions.json", "w") as jf:
    json.dump(intentions, jf, indent=4)


with open("iterate_writing_prompt.json", 'r') as file:
    data = json.load(file)
prompt = data["prompt"]

# prompt = ''' <|begin_of_text|><|start_header_id|>system<|end_header_id|>You are a PhD candidate majoring in computer science and specialize in natural language processing (NLP). You are currently writing a NLP paper targeting the conference on Empirical Methods in Natural Language Processing (EMNLP). 

# Your paper title is {PAPER_TITLE}. Here is what this paper talks about {PAPER_ABSTRACT}

# Here is the current progress of your paper: {CURRENT_TEXT}.<|eot_id|>

# <|start_header_id|>user<|end_header_id|>Your current writing intention is {INTENTION}, {INTENTION_DEFINITION}. Please {VERBALIZER} based on current paper given above. Please reproduce the exact same sentences or words from the current paper provided above, except you want to revise it. No shortcut allowed when reproducing. You are not allowed to talk about yourself.<|eot_id|><|start_header_id|>assistant<|end_header_id|>'''

with open("labels_for_computation.json", 'r') as file:
    labels = json.load(file)

current_time = datetime.datetime.now()
folder_name = current_time.strftime("%m-%d-%y %H:%M")
os.mkdir(folder_name)


PAPER_TITLE = "Threads of Subtlety: Detecting Machine-Generated Texts Through Discourse Motifs"
PAPER_ABSTRACT = "with the advent of large language models (LLMs), distinguishing between machine-generated and human-authored texts has become increasingly challenging. This paper introduces a novel methodology that leverages hierarchical parse trees and recursive hypergraphs to explore the discernible, unique linguistic properties inherent in human-written texts, particularly focusing on their underlying discourse structures beyond mere surface structures. Our empirical findings demonstrate that while both LLMs and humans generate distinct discourse patterns influenced by specific domains, human-written texts exhibit more structural variability, reflecting the nuanced nature of human writing. Notably, incorporating hierarchical discourse features enhances binary classifiers' performance in distinguishing between the two types of texts, even on out-of-distribution and paraphrased samples. This underscores the significance of analyzing hierarchical discourse features and motif analyses in texts, which can highlight subtle structural differences between the author groups depending on their domains. Future plans include extending this approach to long documents by merging multiple document graphs and incorporating topological information beyond discourse."
CURRENT_TEXT = ""


# model_id = "meta-llama/Meta-Llama-3-8B-instruct"
model_id = "meta-llama/Meta-Llama-3-8B"

tokenizer = transformers.AutoTokenizer.from_pretrained(
    model_id,
    token = "",
)

pipeline = transformers.pipeline(
    "text-generation",
    model=model_id,
    tokenizer = tokenizer,
    model_kwargs={"torch_dtype": torch.bfloat16},
    device_map="auto",
    token = "",
    return_full_text= False,
    max_new_tokens = 8000,
    # default hyper-parameter given in the llama 3 repository
    # do_sample= True,
    # temperature= 0.6,
    # max_length= 4096,
    # top_p= 0.9,
    # transformers_version = "4.40.0.dev0"
)

for i in tqdm(range(len(intentions))):
    INTENTION = intentions[i]
    INTENTION_DEFINITION = labels[INTENTION]["definition"]
    if i > 0:
        VERBALIZER = random.choice(labels[INTENTION]["verbalizer"])
    else:
        VERBALIZER = "Create new sections on the paper"
    prompt = prompt.format(PAPER_TITLE = PAPER_TITLE, 
        PAPER_ABSTRACT = PAPER_ABSTRACT, 
        INTENTION = INTENTION,
        INTENTION_DEFINITION = INTENTION_DEFINITION,
        VERBALIZER = VERBALIZER,
        CURRENT_TEXT = CURRENT_TEXT)

    result = pipeline(prompt)
    with open(f"{folder_name}/iteration{i}.txt", 'w') as file:
        file.write(str(current_time)+"\n")
        file.write(f"{INTENTION}: {VERBALIZER}\n以下是语言模型的输出\n")
        file.write(result[0]["generated_text"])

    CURRENT_TEXT = result[0]["generated_text"]