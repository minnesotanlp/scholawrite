for attemp in range(2):
    try:
        import os
        import torch
        from torch import nn, cuda, bfloat16
        from transformers import AutoModelForCausalLM, TrainingArguments, AutoTokenizer, BitsAndBytesConfig, pipeline
        from peft import LoraConfig, get_peft_model, PeftModel
        import accelerate # not used in code but reuqired for device_map='auto'
        from datasets import load_dataset
        from trl import SFTTrainer
        import json
        import random
    except ImportError:
        os.system("pip install --no-cache-dir -r requirements.txt")
        continue

HF_TOKEN = os.getenv("HF_TOKEN")

base_tokenizer = AutoTokenizer.from_pretrained(
    "meta-llama/Meta-Llama-3-8B", 
    token = HF_TOKEN,
)
base_tokenizer.add_special_tokens({'pad_token': '<|end_of_text|>'})


base_model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Meta-Llama-3-8B-Instruct",
    device_map='auto',
    max_memory={0: "48GB", 1: "48GB"},
    token = HF_TOKEN,
    use_cache = False,
)


scholawrite_toeknizer = base_tokenizer
adaptor = "./4th_scholawrite_instruct_adaptor"
scholawrite_model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Meta-Llama-3-8B",
    device_map='auto',
    max_memory={0: "48GB", 1: "48GB"},
    # quantization_config=bnb_config,
    token = HF_TOKEN,
    use_cache = False,
)
scholawrite_model = PeftModel.from_pretrained(scholawrite_model, adaptor)


pipeline1 = pipeline(
    "text-generation",
    model= scholawrite_model,
    tokenizer = scholawrite_toeknizer,
    model_kwargs={"torch_dtype": torch.bfloat16},
    device_map="auto",
    token = "",
    return_full_text= False,
    max_new_tokens = 1000,
    repetition_penalty = 1.5,
    # default hyper-parameter given in the llama 3 repository
    # do_sample= True,
    # temperature= 0.6,
    # max_length= 4096,
    # top_p= 0.9,
    # transformers_version = "4.40.0.dev0"
)

pipeline2 = pipeline(
    "text-generation",
    model= base_model,
    tokenizer = base_tokenizer,
    model_kwargs={"torch_dtype": torch.bfloat16},
    device_map="auto",
    token = "",
    return_full_text= False,
    max_new_tokens = 1000,
    repetition_penalty = 1.5,
    # default hyper-parameter given in the llama 3 repository
    # do_sample= True,
    # temperature= 0.6,
    # max_length= 4096,
    # top_p= 0.9,
    # transformers_version = "4.40.0.dev0"
)

instruct_tune_template="""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are a writing assistant that can generate ideas, implement ideas, and revise paper for scholarly writing. The paper is written in LaTeX. The context of the Paper is provided below, paired with instruction that describes a writing task. Write a response that appropriately completes the request. Do not repeat any instructions. Do not output any instructions. You are not allowed to talk about yourself.<|eot_id|>
<|start_header_id|>user<|end_header_id|>

{BEFORE_TEXT}.

{VERBALIZER}.<|eot_id|>
<|start_header_id|>assistant<|end_header_id|>"""

# you need to create a before.txt by yourself
with open("before_text.txt", 'r') as btf:
    BEFORE_TEXT = btf.read()

VERBALIZER = "Create new sections on the paper"

instruct_tune_template = instruct_tune_template.format(
            VERBALIZER = VERBALIZER,
            BEFORE_TEXT = BEFORE_TEXT
            )

print(instruct_tune_template)

result = pipeline1(instruct_tune_template)

with open("scholawrite_model_output.txt", "w") as sf:
    sf.write(result[0]["generated_text"])

result = pipeline2(instruct_tune_template)

with open("base_model_output.txt", "w") as sf:
    sf.write(result[0]["generated_text"])