import os
from dotenv import load_dotenv
load_dotenv()

from langchain_core.prompts import load_prompt
import openai

openai.api_key = os.getenv('OPEN_AI_API')
system_prompt = load_prompt("./generation_templates/system.yaml")
user_prompt = load_prompt("./generation_templates/user.yaml")

import json

ChatCompletions = []

import pickle


def setup():
    cwd = os.getcwd()
    folders = ["/iterative_prompts", "/iterative_logs", "/iterative_responses"]
    for folder in folders:
        if not os.path.exists(cwd+folder):
            os.makedirs(cwd+folder)
            print(f"{folder} created!")
        else:
            print(f"please remove {folder}")


def get_revise(before_text, i):

    # Save prompt
    with open(f"./iterative_prompts/prompt{i}.json", "w") as f:
        json.dump([
                    {"role": "system", "content": system_prompt.template},
                    {"role": "user", "content": user_prompt.format(before_text=before_text)}
                ], f, indent=4)

    # call chatgpt
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt.template},
            {"role": "user", "content": user_prompt.format(before_text=before_text)}
        ]
    )
    
    # save ChatCompletion object
    with open(f"./iterative_logs/log{i}.txt", "w") as f:
        f.write(str(response))
    ChatCompletions.append(response)

    # rereieve chatgpt response and return to caller
    generated_response = response.choices[0].message.content
    return generated_response

if __name__ == "__main__":
    setup()

    # read seed text from file
    with open("seed.txt", "r") as f:
        seed = f.read()

    for i in range(100):
        response = get_revise(seed, i)

        # write response to file
        with open(f"./iterative_responses/response{i}.txt", "w") as f:
            f.write(response)

        seed = response
    
    with open(f"./iterative_logs/all_logs.pkl", "wb") as f:
        pickle.dump(ChatCompletions, f)
