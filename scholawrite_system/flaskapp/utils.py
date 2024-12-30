import os
import re
from minichain import OpenAI, transform, prompt
from typing import List, Tuple
from config import MEMORY, open_ai_key
from dataclasses import dataclass, replace
import diff_match_patch as dmp_module
import traceback

dmp = dmp_module.diff_match_patch()

os.environ["OPENAI_API_KEY"] = open_ai_key


@transform()
def update(state, chat_output):
    result = chat_output.split("Assistant:")[-1]
    return state.push(result)


@dataclass
class State:
    memory: List[Tuple[str, str]]
    human_input: str = ""

    def push(self, response: str) -> "State":
        memory = self.memory if len(self.memory) < MEMORY else self.memory[1:]
        return State(memory + [(self.human_input, response)])

    def __str__(self):
        return self.memory[-1][-1]


@prompt(OpenAI(), template_file="chat.pmpt.tpl")
def chat_response(model, state: State) -> State:
    return model.stream(state)


def chat(current, state):
    command = current
    state = replace(state, human_input=command)
    return update(state, chat_response(state))


def context_tokenizer(info):
    context_dict = {}
    dmp.Match_Distance = 5000
    start = dmp.match_main(info["current_content"], info["selected_text"], 0)
    end = start + len(info["selected_text"]) - 1

    # if selected text is not a complete sentence
    # Following code will find the closest end of sentence
    for j in range(end, len(info["current_content"]), 1):
        if info["current_content"][j] in ".?!;\n":
            end = j + 1
            break
        end += 1
    for i in range(start, 0, -1):
        if info["current_content"][i] in ".?!;\n":
            start = i + 1
            break
        start -= 1

    context_dict["selected_text"] = info["current_content"][start:end]

    # text on the same line but not selected
    context_dict["same_line_before"] = info["current_content"][:start]
    context_dict["same_line_after"] = info["current_content"][end:]

    # By combining the text content on the other lines
    # with the unselected content on the same line, we get the context.
    # Passing the context to the language model along with the selected content
    context_dict["before"] = info["pre_content"] + context_dict["same_line_before"]
    context_dict["after"] = context_dict["same_line_after"] + info["pos_content"]

    return context_dict


def call_chatgpt(selected_text):
    try:
        suggestion = str(chat(selected_text, State([])).run())
        split_response = re.split(r'-{4,}',suggestion)
        split_response = list(filter(None, split_response))
        if len(split_response) == 2:
            paraphrase = split_response[0].replace("Paraphrase:", "", 1).strip()
            explanation = split_response[1].replace("Explanation:", "", 1).strip()
        else:
            paraphrase = suggestion
            explanation = "ChatGPT respond in a wrong format. Above is its complete response."
    except Exception:
        traceback.print_exc()
        paraphrase = ""
        explanation = ""

    return paraphrase, explanation


def update_database(activity, info, context_dict, gpt_response):
    info["revision"] = [[0, context_dict["before"]],
                        [2, context_dict["selected_text"]],
                        [0, context_dict["after"]]]

    template = "({line_num}, {char_num}), {text}---request for paraphrase"
    info["target"] = template.format(line_num=info["line"],
                                     char_num=len(context_dict["same_line_after"]),
                                     text=context_dict["selected_text"])

    info["suggestion"] = gpt_response[0]
    info["explanation"] = gpt_response[1]

    info.pop("pre_content")
    info.pop("pos_content")
    info.pop("current_content")

    activity.insert_one(info)

    return info


def form_data(context_dict, gpt_response, line):
    diffs_html = ""
    paraphrase = gpt_response[0]
    explanation = gpt_response[1]
    if paraphrase != "":
        diffs = dmp.diff_main(context_dict["selected_text"], paraphrase)
        dmp.diff_cleanupSemantic(diffs)
        diffs_html = dmp.diff_prettyHtml(diffs)

    data = {
        "status": "ChatGPT",
        "suggestion": paraphrase,
        "explanation": explanation,
        "diffs_html": diffs_html,
        "same_line_before": context_dict["same_line_before"],
        "same_line_after": context_dict["same_line_after"],
        "line": line
    }
    return data
