import logging
import pandas as pd
import json
from dataclasses import dataclass, field
import os
import random
import torch
from datasets import load_dataset
from transformers import AutoTokenizer, TrainingArguments
from trl.commands.cli_utils import TrlParser
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
        set_seed,

)
from trl import setup_chat_format
from peft import LoraConfig

from trl import (
   SFTTrainer)

HF_TOKEN = os.getenv("HF_TOKEN")

def formatting_prompts_func(examples):
    BEFORE_TEXTs    = examples["before_text"]
    INTENTIONs      = examples["writing_intention"]
    AFTER_TEXTs     = examples["after_text"]
    
    tune_ready_prompts = []

    for BEFORE_TEXT, INTENTION, AFTER_TEXT in zip(BEFORE_TEXTs, INTENTIONs, AFTER_TEXTs):
        VERBALIZER           = random.choice(labels[INTENTION]["verbalizer"])

        tune_ready_prompt = instruct_tune_template.format(
                            VERBALIZER = VERBALIZER,
                            BEFORE_TEXT = BEFORE_TEXT,
                            AFTER_TEXT = AFTER_TEXT)
        tune_ready_prompts.append(tune_ready_prompt)
    
    return {"tune" : tune_ready_prompts}
pass

def prepare_data():
    if not os.path.exists("test.csv"):
        df = pd.read_csv('fine_tuning.csv')
        random_row = df.sample(n=28)
        random_row.to_csv('test.csv', index=False)
        df = df.drop(random_row.index)
        df.to_csv('fine_tuning.csv', index=False)

    with open("labels_for_computation.json", 'r') as lf:
        labels = json.load(lf)

    tokenizer = AutoTokenizer.from_pretrained("meta-llama/Meta-Llama-3-8B", token = HF_TOKEN)
    tokenizer.pad_token = tokenizer.eos_token

    instruct_tune_template="""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

    You are a writing assistant that can generate ideas, implement ideas, and revise paper for scholarly writing. The paper is written in LaTeX. The context of the Paper is provided below, paired with instruction that describes a writing task. Write a response that appropriately completes the request. Do not repeat any instructions. Do not output any instructions. You are not allowed to talk about yourself.<|eot_id|>
    <|start_header_id|>user<|end_header_id|>
    
    {BEFORE_TEXT}.
    
    {VERBALIZER}.<|eot_id|>
    <|start_header_id|>assistant<|end_header_id|>
    
    {AFTER_TEXT}<|eot_id|>"""

    dataset = load_dataset("csv", data_files={"train": "fine_tuning.csv",
                                                "test": "test.csv"})
    dataset = dataset.map(formatting_prompts_func, batched = True)


def training_function(script_args, training_args):
    torch_dtype = torch.bfloat16
    quant_storage_dtype = torch.bfloat16

    quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch_dtype,
            bnb_4bit_quant_storage=quant_storage_dtype,
    )

    model = AutoModelForCausalLM.from_pretrained(
        "meta-llama/Meta-Llama-3-8B",
        quantization_config=quantization_config,
        attn_implementation="sdpa", # use sdpa, alternatively use "flash_attention_2"
        torch_dtype=quant_storage_dtype,
        use_cache=False if training_args.gradient_checkpointing else True,  # this is needed for gradient checkpointing
    )

    if training_args.gradient_checkpointing:
        model.gradient_checkpointing_enable()

    ################
    # PEFT
    ################

    # LoRA config based on QLoRA paper & Sebastian Raschka experiment
    peft_config = LoraConfig(
        lora_alpha=8,
        lora_dropout=0.05,
        r=16,
        bias="none",
        target_modules="all-linear",
        task_type="CAUSAL_LM",
        modules_to_save = ["lm_head", "embed_tokens"] # add if you want to use the Llama 3 instruct template
    )

    ################
    # Training
    ################
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset["train"],
        dataset_text_field="text",
        eval_dataset=dataset["test"],
        peft_config=peft_config,
        max_seq_length=script_args.max_seq_length,
        tokenizer=tokenizer,
        packing=True,
        dataset_kwargs={
            "add_special_tokens": False,  # We template with special tokens
            "append_concat_token": False,  # No need to add additional separator token
        },
    )
    if trainer.accelerator.is_main_process:
        trainer.model.print_trainable_parameters()

    ##########################
    # Train model
    ##########################
    checkpoint = None
    if training_args.resume_from_checkpoint is not None:
        checkpoint = training_args.resume_from_checkpoint
    trainer.train(resume_from_checkpoint=checkpoint)

    ##########################
    # SAVE MODEL FOR SAGEMAKER
    ##########################
    if trainer.is_fsdp_enabled:
        trainer.accelerator.state.fsdp_plugin.set_state_dict_type("FULL_STATE_DICT")
    
    merged_model = model.merge_and_unload()
    merged_model.save_pretrained(training_args.output_dir,safe_serialization=True)


@dataclass
class ScriptArguments:
    dataset_path: str = field(
        default=None,
        metadata={
            "help": "Path to the dataset"
        },
    )
    model_id: str = field(
        default=None, metadata={"help": "Model ID to use for SFT training"}
    )
    max_seq_length: int = field(
        default=512, metadata={"help": "The maximum sequence length for SFT Trainer"}
    )



if __name__ == "__main__":
    parser = TrlParser((ScriptArguments, TrainingArguments))
    script_args, training_args = parser.parse_args_and_config()    

    # set use reentrant to False
    if training_args.gradient_checkpointing:
        training_args.gradient_checkpointing_kwargs = {"use_reentrant": True}
    # set seed
    set_seed(training_args.seed)

    # launch training
    training_function(script_args, training_args)