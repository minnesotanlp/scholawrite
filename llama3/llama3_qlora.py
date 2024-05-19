for attemp in range(2):
    try:
        import os
        import torch
        from torch import nn, cuda, bfloat16
        from transformers import AutoModelForCausalLM, TrainingArguments, AutoTokenizer, BitsAndBytesConfig, pipeline
        from peft import LoraConfig, get_peft_model
        import accelerate # not used in code but reuqired for device_map='auto'
        from datasets import load_dataset
        from trl import SFTTrainer
        import json
        import random
    except ImportError:
        os.system("pip install --no-cache-dir -r requirements.txt")
        continue

device = f'cuda:{cuda.current_device()}' if cuda.is_available() else 'cpu'
print(device)

HF_TOEKN = ""

tokenizer = AutoTokenizer.from_pretrained(
    "meta-llama/Meta-Llama-3-8B", 
    token = HF_TOEKN,
)
tokenizer.add_special_tokens({'pad_token': '<|end_of_text|>'})

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type='nf4',
    bnb_4bit_use_double_quant=True,
    bnb_4bit_compute_dtype=bfloat16
)

model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Meta-Llama-3-8B",
    device_map='auto',
    max_memory={0: "48GB", 1: "48GB"},
    quantization_config=bnb_config,
    token = HF_TOEKN,
)


with open("labels_for_computation.json", 'r') as file:
    labels = json.load(file)



# instruct_prompt = """<|begin_of_text|><|start_header_id|>system<|end_header_id|>You are a PhD candidate majoring in computer science and specialize in natural language processing (NLP). You are currently writing a NLP paper targeting the conference. The paper is written in LaTeX.

# Here is the current progress of your paper: {BEFORE_TEXT}.

# <|eot_id|><|start_header_id|>user<|end_header_id|>Your current writing intention is {INTENTION}, {INTENTION_DEFINITION}. Please {VERBALIZER} based on current paper given above.

# <|eot_id|><|start_header_id|>assistant<|end_header_id|>{AFTER_TEXT}"""


new_prompt = """Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.

### Instruction:
{VERBALIZER}

### Input:
{BEFORE_TEXT}

### Response:
{AFTER_TEXT}"""


EOS_TOKEN = tokenizer.eos_token # Must add EOS_TOKEN

# def formatting_prompts_func(examples):
#     BEFORE_TEXTs    = examples["before_text"]
#     INTENTIONs      = examples["writing_intention"]
#     AFTER_TEXTs     = examples["after_text"]
    
#     tune_ready_prompts = []

#     for BEFORE_TEXT, INTENTION, AFTER_TEXT in zip(BEFORE_TEXTs, INTENTIONs, AFTER_TEXTs):

#         INTENTION_DEFINITION = labels[INTENTION]["definition"]
#         VERBALIZER           = random.choice(labels[INTENTION]["verbalizer"])

#         tune_ready_prompt = instruct_prompt.format(INTENTION = INTENTION,
#                                INTENTION_DEFINITION = INTENTION_DEFINITION,
#                                VERBALIZER = VERBALIZER,
#                                BEFORE_TEXT = BEFORE_TEXT,
#                                AFTER_TEXT = AFTER_TEXT)
#         tune_ready_prompt += EOS_TOKEN
#         tune_ready_prompts.append(tune_ready_prompt)
    
#     return {"tune" : tune_ready_prompts}
# pass


def formatting_prompts_func(examples):
    BEFORE_TEXTs    = examples["before_text"]
    INTENTIONs      = examples["writing_intention"]
    AFTER_TEXTs     = examples["after_text"]
    
    tune_ready_prompts = []

    for BEFORE_TEXT, INTENTION, AFTER_TEXT in zip(BEFORE_TEXTs, INTENTIONs, AFTER_TEXTs):
        VERBALIZER           = random.choice(labels[INTENTION]["verbalizer"])

        tune_ready_prompt = new_prompt.format(
                               VERBALIZER = VERBALIZER,
                               BEFORE_TEXT = BEFORE_TEXT,
                               AFTER_TEXT = AFTER_TEXT)
        tune_ready_prompt += EOS_TOKEN
        tune_ready_prompts.append(tune_ready_prompt)
    
    return {"tune" : tune_ready_prompts}
pass

dataset = load_dataset("csv", data_files={"train": "fine_tuning.csv"})
dataset = dataset.map(formatting_prompts_func, batched = True,)

print(dataset["train"])
print(dataset["train"]["tune"][0])

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

config = LoraConfig(
    r = 16, # Choose any number > 0 ! Suggested 8, 16, 32, 64, 128
    target_modules = ["q_proj", "k_proj", "v_proj", "o_proj",
                      "gate_proj", "up_proj", "down_proj"],
    lora_alpha = 16,  # From unsloth
    lora_dropout = 0, # Supports any, but = 0 is optimized
    bias = "none",    # Supports any, but = "none" is optimized
    # use_rslora = True, # Better perfformance with similar computing cost https://huggingface.co/docs/peft/main/en/package_reference/lora#peft.LoraConfig.use_rslora
    # loftq_config = LoftQConfig(loftq_bits=8), # Minimize error, Improve performance. huggingface.co/docs/peft/v0.8.0/en/developer_guides/quantization#loftq-initialization
    task_type="CAUSAL_LM" # set this for CLM or Seq2Seq
)

model = get_peft_model(model, config)
print_trainable_parameters(model)

trainer = SFTTrainer(
    model = model,
    tokenizer = tokenizer,
    train_dataset = dataset["train"],
    dataset_text_field = "tune",
    max_seq_length = 3500,
    # packing = False, # Can make training 5x faster for short sequences.
    args = TrainingArguments(
        per_device_train_batch_size = 1,
        gradient_accumulation_steps = 4,
        warmup_steps = 5,
        learning_rate = 2e-4,
        fp16 = not torch.cuda.is_bf16_supported(),
        bf16 = torch.cuda.is_bf16_supported(),
        logging_steps = 1,
        optim = "adamw_8bit",
        weight_decay = 0.01,
        lr_scheduler_type = "linear",
        seed = 3407,
        output_dir = "outputs",
        num_train_epochs= 5,
    ),
)

trainer_stats = trainer.train()

merged_model = model.merge_and_unload()
merged_model.save_pretrained("3rd_scholawrite_instruct_llama")

# model.push_to_hub("BbRrOoKk/2st_scholawrite_instruct_llama", token = HF_TOEKN)