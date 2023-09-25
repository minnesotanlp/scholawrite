from minichain import OpenAI, transform
from typing import List, Tuple
from config import MEMORY

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
    command = "Please paraphrase this sentence/paragraph: \n\"" + current + "\"\nThen explain to me methods you use with examples from paraphrased paragraph." \
                "The length of sentence should not be too long or too short than previous one." \
                "Feel Free to use any methods that are appropriate for scholarly writing, but total number of methods using should not be more than four. \n" \
                "Your response format should be looks like this: \n\"" \
                "Paraphrase: [Paraphrased paragraph]\n" \
                "---------------------------------------------------------\n" \
                "Explanation: [Explanation of the paraphrase].\"\n" \
                "You must include \"---------------------------------------------------------\" between paraphrase and explanation!"
    state = replace(state, human_input=command)
    return update(state, chat_response(state))
    
