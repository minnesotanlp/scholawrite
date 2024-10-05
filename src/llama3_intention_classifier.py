import os
import pandas as pd
import torch
from torch.distributed.fsdp import FullyShardedDataParallel as FSDP
from torch.distributed.fsdp import CPUOffload
import torch.distributed as dist
from torch import cuda, bfloat16
from transformers import AutoModelForCausalLM, Trainer, TrainingArguments, AutoTokenizer, BitsAndBytesConfig, pipeline
from datasets import Dataset
from peft import LoraConfig, get_peft_model
import accelerate # not used in code but reuqired for device_map='auto'
from datasets import load_dataset
import datasets
from trl import SFTTrainer
import json
import random
import matplotlib.pyplot as plt

import args

#from dataset_utils import 

def load_model(model_name):
    #bnb_config = BitsAndBytesConfig(
    #    load_in_4bit=True,
    #    bnb_4bit_quant_type='nf4',
    #    bnb_4bit_use_double_quant=True,
    #    bnb_4bit_compute_dtype=bfloat16
    #)

    model = AutoModelForCausalLM.from_pretrained(
        #"meta-llama/Meta-Llama-3-8B",
        model_name,
        device_map='auto',
        #max_memory={0: "48GB", 1: "48GB"},
        max_memory={0: "15GB", 1: "15GB"},
        #quantization_config=bnb_config,
        #token = HF_TOKEN,
        use_cache = False,
    )
    
    # model = FSDP(model)
    return model

def get_quantized_model(model):
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
    #print_trainable_parameters(model)

    return model


def load_tokenizer(model_name):
    tokenizer = AutoTokenizer.from_pretrained(
        #"meta-llama/Meta-Llama-3-8B", 
        model_name,
        #token = HF_TOKEN,
    )

    return tokenizer

def get_causal_lm_trainer(model, tokenizer, dataset):
  training_args = TrainingArguments(
      output_dir = f"{args.OUTPUT_DIR}",
      logging_dir= f"{args.LOG_DIR}",
      logging_steps = 1,
      per_device_train_batch_size = 1,
      per_device_eval_batch_size = 1,
      gradient_accumulation_steps = 4,
      warmup_steps = 5,
      learning_rate = 2e-4,
      fp16 = not torch.cuda.is_bf16_supported(),
      bf16 = torch.cuda.is_bf16_supported(),
      optim = "adamw_8bit",
      weight_decay = 0.01,
      lr_scheduler_type = "linear",
      seed = 3407,
      num_train_epochs= 5,
      evaluation_strategy = "steps",
      eval_accumulation_steps=100,
      gradient_checkpointing = True,
      # report_to = "tensorboard"
  )

  trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=dataset["train"],
    eval_dataset=dataset["test"],
    tokenizer=tokenizer
  )

  return trainer

def setup_sftt_trainer(model, tokenizer, dataset):
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
            output_dir = f"{args.OUTPUT_DIR}",
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
            evaluation_strategy = "steps",
            eval_accumulation_steps=100,
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