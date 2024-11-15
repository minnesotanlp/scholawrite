import os
import json
from tqdm import tqdm
from dotenv import load_dotenv
load_dotenv()

import openai
openai.api_key = os.getenv('OPEN_AI_API')

from one_time_inference_prompt import one_time_inference_prompt


def setup():
    cwd = os.getcwd()

    folders = ["gpt4o_output"]
    
    for folder in folders:
        os.makedirs(os.path.join(cwd, folder), exist_ok = True)
        print(f"{folder} created!")


def get_gpt_writing(seedname, before_text):
    prompt = one_time_inference_prompt(before_text)

    # Save prompt
    with open(f"./gpt4o_output/{seedname}_prompt.json", "w") as f:
        json.dump(prompt,
                   f, 
                   indent=4)

    # call chatgpt
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages= prompt
    )

    # save ChatCompletion object
    with open(f"./gpt4o_output/{seedname}_log.txt", "w") as f:
        f.write(str(response))

    # rereieve chatgpt response and return to caller
    generated_response = response.choices[0].message.content
    return generated_response



if __name__ == "__main__":
    setup()

    seeds = ["seed1", "seed2", "seed3", "seed4"]

    for each in tqdm(seeds):
        with open(f"../seeds/{each}.txt", "r") as f:
            seed = f.read()

        response = get_gpt_writing(each, seed)

        with open(f"./gpt4o_output/{each}_result.txt", 'w') as file:
            file.write(response)
