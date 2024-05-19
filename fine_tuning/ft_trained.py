for attemp in range(2):
    try:
        import os
        import pandas as pd
        import torch
        from pymongo import MongoClient
        from torch.distributed.fsdp import FullyShardedDataParallel as FSDP
        from torch.distributed.fsdp import CPUOffload
        import torch.distributed as dist
        from torch import cuda, bfloat16
        from transformers import AutoModelForCausalLM, TrainingArguments, AutoTokenizer, BitsAndBytesConfig, pipeline
        from peft import LoraConfig, get_peft_model
        import accelerate # not used in code but reuqired for device_map='auto'
        from datasets import load_dataset
        from trl import SFTTrainer
        import json
        import random
        from dotenv import load_dotenv
    except ImportError:
        os.system("pip install --no-cache-dir -r requirements.txt")
        continue

load_dotenv()

load_dotenv()

HF_TOKEN = os.environ["HUGGINGFACE_API_KEY"]

debug = False
device = 'cuda' if debug == False and torch.cuda.is_available() else 'cpu'

def print_trainable_parameters(model):
    """
    Prints the number of trainable parameters in the model.
    """
    trainable_params = 0
    all_param = 0
    for _, param in model.named_parameters():
        all_param += param.numel()
        if param.requires_grad:
            trainable_params += param.numel()
    print(
        f"trainable params: {trainable_params} || all params: {all_param} || trainable%: {100 * trainable_params / all_param}"
    )

def load_model():
    # bnb_config = BitsAndBytesConfig(
    #     load_in_4bit=True,
    #     bnb_4bit_quant_type='nf4',
    #     bnb_4bit_use_double_quant=True,
    #     bnb_4bit_compute_dtype=bfloat16
    # )

    model = AutoModelForCausalLM.from_pretrained(
        "meta-llama/Meta-Llama-3-8B",
        device_map='auto',
        max_memory={0: "48GB", 1: "48GB"},
        # quantization_config=bnb_config,
        token = HF_TOKEN,
        use_cache = False,
    )

    
    # model = FSDP(model)

    config = LoraConfig(
        r = 16,                                         # Choose any number > 0 ! Suggested 8, 16, 32, 64, 128
        target_modules = "all-linear",
        lora_alpha = 16,                                # From unsloth
        lora_dropout = 0,                               # Supports any, but = 0 is optimized
        bias = "none",                                  # Supports any, but = "none" is optimized
        # use_rslora = True,                            # Better perfformance with similar computing cost https://huggingface.co/docs/peft/main/en/package_reference/lora#peft.LoraConfig.use_rslora
        # loftq_config = LoftQConfig(loftq_bits=8),     # Minimize error, Improve performance. huggingface.co/docs/peft/v0.8.0/en/developer_guides/quantization#loftq-initialization
        task_type="CAUSAL_LM",                          # set this for CLM or Seq2Seq
        modules_to_save = ["lm_head", "embed_tokens"],   # if we want to use the special tokens and template from Llama 3 instruct for Lorac
    )

    model = get_peft_model(model, config)
    print_trainable_parameters(model)

    return model


def get_dataset():
  client = MongoClient('localhost', 5001)

  db = client.dataset_db
  annotation = db.fine_tuning
  query = {}
  cursor = annotation.find(query)

  activity_df = pd.DataFrame(list(cursor))

  idx = 30

  before_text = activity_df["before_text"].iloc[idx]
  diff_arr = activity_df["diff_array"]
  writing_intention = activity_df["writing_intention"].iloc[idx]

  diff_text = ""

  for diff in diff_arr.iloc[0]:
    diff = diff[:2]
    key = diff[0]
    text = diff[1]

    if (key == 0):
      diff_text += text
    elif(key == 1):
      diff_text += "[ADD]"
      diff_text += text
      diff_text += "[/ADD]"
    elif(key == -1):
      diff_text += "[DEL]"
      diff_text += text
      diff_text += "[/DEL]"
    
  verbalizer = "Draft a paragraph of full sentences in the body of the paper"

  return writing_intention, before_text, diff_text

def formatting_prompts_func(w_intention, b_text, d_text):
    instruct_tune_template="""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are a writing assistant that can generate ideas, implement ideas, and revise paper for scholarly writing. The paper is written in LaTeX. The context of the Paper is provided below, paired with instruction that describes a writing task. Write a response that appropriately completes the request. Do not repeat any instructions. Do not output any instructions. You are not allowed to talk about yourself.<|eot_id|>
<|start_header_id|>user<|end_header_id|>

{BEFORE_TEXT}.

{VERBALIZER}.<|eot_id|>
<|start_header_id|>assistant<|end_header_id|>

{AFTER_TEXT}<|eot_id|>"""

    #BEFORE_TEXTs    = examples["before_text"]
    #INTENTIONs      = examples["writing_intention"]
    #AFTER_TEXTs     = examples["after_text"]


    BEFORE_TEXTs    = b_text
    INTENTIONs      = w_intention
    AFTER_TEXTs     = d_text
    
    tune_ready_prompts = []

    for BEFORE_TEXT, INTENTION, AFTER_TEXT in zip(BEFORE_TEXTs, INTENTIONs, AFTER_TEXTs):
        VERBALIZER           = random.choice(labels[INTENTION]["verbalizer"])

        tune_ready_prompt = instruct_tune_template.format(
                            VERBALIZER = VERBALIZER,
                            BEFORE_TEXT = BEFORE_TEXT,
                            AFTER_TEXT = AFTER_TEXT)
        tune_ready_prompts.append(tune_ready_prompt)
    
    return {"tune" : tune_ready_prompts}


def prepare_data():
    if not os.path.exists("test.csv"):
        df = pd.read_csv('fine_tuning.csv')
        random_row = df.sample(n=44)
        random_row.to_csv('test.csv', index=False)
        df = df.drop(random_row.index)
        df.to_csv('fine_tuning.csv', index=False)

    dataset = load_dataset("csv", data_files={"train": "fine_tuning.csv",
                                                "test": "test.csv"})
    dataset = dataset.map(formatting_prompts_func, batched = True)
    
    return dataset

def load_toeknizer():
    tokenizer = AutoTokenizer.from_pretrained(
        "meta-llama/Meta-Llama-3-8B", 
        token = HF_TOKEN,
    )
    tokenizer.add_special_tokens({'pad_token': '<|end_of_text|>'})

    return tokenizer

def tokenize(text):
  return tokenizer.encode(text)

def tokenize_input(verbalizer, before_text):
  text = f'<s> [INST] {verbalizer} [/INST]\n{before_text}'
  print(text)
  return tokenizer(text, return_tensors='pt').to(device)


verbalizer, before_text, diff_text = get_dataset()

messages = [
    {
        "role": "system",
        "content": verbalizer,
    },
    {   "role": "user", 
        "content": before_text
    },
 ]

it = tokenizer.apply_chat_template(messages, tokenize=False)

tokenized_chat = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True, return_tensors="pt").to(device)

print("BEFORE TEXT: \n\n\n", tokenizer.decode(tokenized_chat[0]))

outputs = model.generate(tokenized_chat, max_new_tokens=4000)

print("--------------------\nOUTPUT\n\n", tokenizer.decode(outputs[0]))






