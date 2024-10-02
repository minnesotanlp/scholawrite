from langchain_core.prompts import load_prompt
import json
import openai
import os

openai.api_key = os.getenv("OPEN_AI_KEY")
system_prompt = load_prompt("./prompt_template/system.yaml")
user_prompt = load_prompt("./prompt_template/user.yaml")

with open("labels_for_computation.json", 'r') as lf:
    labels = json.load(lf)

def get_revise(before_text, label):
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt.format(before_text=before_text, label=label, definition=labels[label]["definition"])}
        ]
    )
    print(response)
    generated_prompt = response.choices[0].message.content
    return generated_prompt

if __name__ == "__main__":
    get_revise()