import os
import pandas as pd
import torch
from torch.distributed.fsdp import FullyShardedDataParallel as FSDP
from torch.distributed.fsdp import CPUOffload
import torch.distributed as dist
from torch import cuda, bfloat16
from transformers import AutoModelForCausalLM, TrainingArguments, AutoTokenizer, BitsAndBytesConfig, pipeline
from datasets import Dataset
from peft import LoraConfig, get_peft_model
import accelerate # not used in code but reuqired for device_map='auto'
from datasets import load_dataset
import datasets
from trl import SFTTrainer
import json
import random
from dotenv import load_dotenv
from pymongo import MongoClient


load_dotenv()

HF_TOKEN = os.environ["HUGGINGFACE_API_KEY"]

with open("labels_for_computation.json", 'r') as file:
    labels = json.load(file)

def formatting_prompts_func(row):
    instruct_tune_template="""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are a writing assistant that can generate ideas, implement ideas, and revise paper for scholarly writing. The paper is written in LaTeX. The context of the Paper is provided below, paired with instruction that describes a writing task. Write a response that appropriately completes the request. Do not repeat any instructions. Do not output any instructions. You are not allowed to talk about yourself.<|eot_id|>
<|start_header_id|>user<|end_header_id|>

{BEFORE_TEXT}.

{VERBALIZER}.<|eot_id|>
<|start_header_id|>assistant<|end_header_id|>

{AFTER_TEXT}<|eot_id|>"""

    BEFORE_TEXT    = row["before_text"]
    INTENTION      = row["writing_intention"]
    AFTER_TEXT     = row["new_diff"]
    VERBALIZER           = random.choice(labels[INTENTION]["verbalizer"])

    tune_ready_prompt = instruct_tune_template.format(
                        VERBALIZER = VERBALIZER,
                        BEFORE_TEXT = BEFORE_TEXT,
                        AFTER_TEXT = AFTER_TEXT)
  
    return tune_ready_prompt
    #return {"tune" : tune_ready_prompts}

def get_dataset():
  client = MongoClient('localhost', 5001)

  db = client.dataset_db
  annotation = db.fine_tuning
  query = {}
  cursor = annotation.find(query)

  activity_df = pd.DataFrame(list(cursor))

  idx = 30

  def diff_to_text(diff_arr):
    diff_text = ""

    for diff in diff_arr:
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
      
    return diff_text

  print("columns", activity_df.columns)

  activity_df["new_diff"] = activity_df["diff_array"].apply(lambda x: diff_to_text(x))
  activity_df["input"] = activity_df.apply(formatting_prompts_func, axis=1)

  length = len(activity_df)

  dataset = datasets.DatasetDict(
    {
        "train": Dataset.from_pandas(activity_df.loc[0:int(length * 0.9), ["input", "new_diff"]]),
        "test": Dataset.from_pandas(activity_df.loc[int(length * 0.9):, ["input", "new_diff"]]),
    })

#  dataset = datasets.DatasetDict(
#    {
#        "train": Dataset.from_pandas(activity_df.loc[0:10, ["input", "new_diff"]]),
#        "test": Dataset.from_pandas(activity_df.loc[10:20, ["input", "new_diff"]]),
#    })
  
  return dataset

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


def load_toeknizer():
    tokenizer = AutoTokenizer.from_pretrained(
        "meta-llama/Meta-Llama-3-8B", 
        token = HF_TOKEN,
    )
    tokenizer.add_special_tokens({'pad_token': '<|end_of_text|>'})

    return tokenizer


def setup_trainer(model, tokenizer, dataset):
    trainer = SFTTrainer(
        model = model,
        tokenizer = tokenizer,
        train_dataset = dataset["train"],
        eval_dataset=dataset["test"],
        dataset_text_field = "input",
        max_seq_length = 4581,
        # packing = False, # Can make training 5x faster for short sequences.
        dataset_kwargs={
            "add_special_tokens": False,  # We template with special tokens
            "append_concat_token": False,  # No need to add additional separator token
        },
        args = TrainingArguments(
            output_dir = "output",
            per_device_train_batch_size = 1,
            per_device_eval_batch_size = 1,
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
            num_train_epochs= 5,
            evaluation_strategy = "epoch",
            gradient_checkpointing = True,
            # report_to = "tensorboard"
        ),
    )

    return trainer


# def setup_fsdp():
#     rank = int(os.environ['LOCAL_RANK'])
#     os.environ['MASTER_ADDR'] = 'localhost'
#     os.environ['MASTER_PORT'] = '12345'
#     dist.init_process_group("nccl", rank=rank, world_size=2)
#     torch.cuda.set_device(rank)


def fine_max_tokens_length(dataset, tokenizer):
    print(dataset)
    
    max = 0
    for each in dataset["train"]["input"]:
        tokens = tokenizer(each)
        if max < len(tokens["input_ids"]):
            max = len(tokens["input_ids"])
    for each in dataset["test"]["input"]:
        tokens = tokenizer(each)
        if max < len(tokens["input_ids"]):
            max = len(tokens["input_ids"])
    
    print("Max sequence length in the dataset:", max)
    return max


def main():
    print(accelerate.Accelerator().device)
    print(accelerate.Accelerator().state)
    # setup_fsdp()

    tokenizer = load_toeknizer()

    dataset = get_dataset()
    fine_max_tokens_length(dataset, tokenizer)

    model = load_model()

    trainer = setup_trainer(model, tokenizer, dataset)

    train_results = trainer.train()

    trainer.log_metrics("train", train_results.metrics)

    trainer.save_metrics("train", train_results.metrics)

    print("\n\n")
    print(trainer.state.log_history)
    print("\n\n")

    trainer.save_state()

    merged_model = model.merge_and_unload()
    merged_model.save_pretrained("qlora_2nd", safe_serialization=True)
    # model.push_to_hub("BbRrOoKk/2st_scholawrite_instruct_llama", token = HF_TOKEN)

    # dist.destroy_process_group()


if __name__ == "__main__":
    main()