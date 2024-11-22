def get_system_prompt():
    system_prompt="You are a computer science researcher with extensive experience of scholarly writing. Here, you are writing a research paper in natural language processing using LaTeX languages."
    return system_prompt

def get_user_prompt(seed_text):
    user_prompt= f"""Below is the work-in-progress paper with a title and abstract. Please complete this paper, focusing on expanding upon the content and ideas introduced. Your writing should align closely with the tone, style, and subject matter already established in the title and abstract. Please give a complete output. Do not generate text other than the paper, nor extraneous text outside of the paper content.
    
    {seed_text}
    """
    return user_prompt


def one_time_inference_prompt(before_text):
    return [
            {"role": "system", "content": get_system_prompt()},
            {"role": "user", "content": get_user_prompt(before_text)}
            ]