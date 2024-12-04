import os
from dotenv import load_dotenv
load_dotenv()

from prompt import text_gen_prompt, class_prompt

import openai
openai.api_key = os.getenv('OPEN_AI_API')

import json
from tqdm import tqdm

def setup(seed_name):
  global generation_dir, intention_dir, generation_raw_dir, intention_raw_dir, generation_log_dir, intention_log_dir, generation_prompt_dir, intention_prompt_dir, path_to_seed

  output_dir = os.path.join("/workspace/gpt4o_output/", seed_name)

  generation_dir = f"{output_dir}/generation"
  intention_dir = f"{output_dir}/intention"

  generation_raw_dir = f"{output_dir}/generation_raw"
  intention_raw_dir = f"{output_dir}/intention_raw"

  generation_log_dir = f"{output_dir}/generation_log"
  intention_log_dir = f"{output_dir}/intention_log"

  generation_prompt_dir = f"{output_dir}/generation_prompt"
  intention_prompt_dir = f"{output_dir}/intention_prompt"

  os.makedirs(generation_dir, exist_ok=True)
  os.makedirs(intention_dir, exist_ok=True)

  os.makedirs(generation_raw_dir, exist_ok=True)
  os.makedirs(intention_raw_dir, exist_ok=True)

  os.makedirs(generation_log_dir, exist_ok=True)
  os.makedirs(intention_log_dir, exist_ok=True)

  os.makedirs(generation_prompt_dir, exist_ok=True)
  os.makedirs(intention_prompt_dir, exist_ok=True)

  path_to_seed = os.path.join("/workspace/scholawrite/seeds", f"{seed_name}.txt")


def load_seed(fname):
  with open(fname, 'r') as file:
    content = file.read()
  return content


def save_raw_output(output, writing_intention, i):
  with open(f"{generation_raw_dir}/iter_generation_{i}.txt", "w") as file:
    file.write(output)

  with open(f"{intention_raw_dir}/iter_intention_{i}.txt", "w") as file:
    file.write(writing_intention)


def get_label(before_text, i):
    prompt = class_prompt(before_text)
    # Save prompt
    with open(f"{intention_prompt_dir}/iter_prompt_{i}.json", "w") as f:
        json.dump(prompt, f, indent=4)

    # call chatgpt
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=prompt
    )

    # save ChatCompletion object
    with  open(f"{intention_log_dir}/iter_log_{i}.json", "w") as f:
        json.dump(response.model_dump(), f, indent=4)

    # rereieve chatgpt response and return to caller
    generated_response = response.choices[0].message.content
    return generated_response


def process_label(predicted_label):
    all_labels = ['Text Production', 'Visual Formatting', 'Clarity', 'Section Planning',
 'Structural', 'Object Insertion', 'Cross-reference', 'Fluency',
 'Idea Generation', 'Idea Organization', 'Citation Integration', 'Coherence',
 'Linguistic Style', 'Scientific Accuracy', 'Macro Insertion']

 
    if predicted_label not in all_labels:
        found = 0
        for true_label in all_labels:
            if true_label in predicted_label:
                predicted_label = true_label
                found = 1
                break
        
        # If the output from gpt didn't contain any expeceted label
        if found != 1:
            print(predicted_label)
            print("-" * 100)
            predicted_label = "Text Production"
    
    return predicted_label


def get_revise(before_text, label, i):

    label = process_label(label)

    prompt = text_gen_prompt(before_text, label)
    # Save prompt
    with open(f"{generation_prompt_dir}/iter_prompt_{i}.json", "w") as f:
        json.dump(prompt, f, indent=4)

    # call chatgpt
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=prompt
    )
    
    # save ChatCompletion object
    with open(f"{generation_log_dir}/iter_log_{i}.json", "w") as f:
         json.dump(response.model_dump(), f, indent=4)

    # rereieve chatgpt response and return to caller
    generated_response = response.choices[0].message.content
    return generated_response


def aggregate_iterative_writing():
  prev_writing = load_seed(path_to_seed)
  pbar = tqdm(total=100)

  i = 0
  j = 0 # j represent the true number of iteration, which regardless intentions

  while i < 5:
    writing_intention = get_label(prev_writing, j)

    output = get_revise(prev_writing, writing_intention, j)

    # save the intermediate output in case this intention is same as previous
    save_raw_output(output, writing_intention, j)

    # if this is the model's first output, we don't compare.
    # We setup the previous intention and writing for comparison in future iterations
    if j == 0 :
      prev_intention = writing_intention
      prev_writing = output

    # if current writing intetion is same as previous,
    # we let the model revise it again in the same iteration (i).
    elif writing_intention == prev_intention:
      prev_writing = output

    # if current writing intetion is NOT same as previous,
    # we save the model's aggreated writing to the file.
    # Then move on to next iteration
    else:
      with open(f"{generation_dir}/iter_generation_{i}.txt", "w") as file:
        file.write(prev_writing)

      with open(f"{intention_dir}/iter_intention_{i}.txt", "w") as file:
        file.write(prev_intention)
      
      prev_writing = output
      prev_intention = writing_intention

      i += 1
      pbar.update(1)

    j += 1


def main():
  for each in ["seed1", "seed2", "seed3", "seed4"]:
    print(f"Working on {each}")
    setup(each)
    aggregate_iterative_writing()
    print("-"*100)


if __name__ == "__main__":
  main()