import os

import torch
import pandas as pd
import accelerate
from dotenv import load_dotenv
from huggingface_hub import login
from datasets import Dataset, load_dataset, DatasetDict
from transformers import TrainingArguments, DataCollatorForSeq2Seq, DataCollatorForLanguageModeling
from trl import SFTConfig, SFTTrainer
from unsloth import FastLanguageModel, is_bfloat16_supported
from unsloth.chat_templates import train_on_responses_only

import args
#import taxonomy
#from llama3_intention_classifier import load_tokenizer, load_model, get_quantized_model, get_causal_lm_trainer
import dataset_utils
from dataset_utils import add_special_tokens, get_scholawrite_dataset, get_dataset_statistics, get_dataset_from_df, get_intention_inference_instruction_dataset
#from classification_utils import generate_train_template
from prompt import class_prompt_train

def main():
  load_dotenv()

  HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
  login(token=HUGGINGFACE_TOKEN)

  print(accelerate.Accelerator().device)
  print(accelerate.Accelerator().state)

  #if (args.MODEL_TYPE == "llm"):
  #  #tokenizer = load_tokenizer(args.MODEL_NAME)
  #  #model = load_model(args.MODEL_NAME)
  #elif(args.MODEL_TYPE == "small-lm"):
  #  raise Exception("not implemented")
  #else:
  #  raise Exception("not implemented")

  full_ds = load_dataset("minnesotanlp/scholawrite", revision="anonymous_data")

  #full_ds = DatasetDict({
  #  'train': full_ds["train"].select(range(100)),
  #  'test': full_ds["test"].select(range(100))
  #})

  RELEVANT_CLASSES = set(full_ds["train"]["label"]).union(set(full_ds["test"]["label"]))

  MAX_INPUT_LENGTH = 4096 
  MAX_GEN_LENGTH = MAX_INPUT_LENGTH + 3

  model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/Llama-3.2-3B-Instruct-bnb-4bit",
    max_seq_length=4096,
    load_in_4bit=True,
    dtype=None,
  )
  add_special_tokens(tokenizer, RELEVANT_CLASSES)
  model.resize_token_embeddings(len(tokenizer))

  model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    lora_alpha=16,
    lora_dropout=0,
    target_modules=["q_proj", "k_proj", "v_proj", "up_proj", "down_proj", "o_proj", "gate_proj"],
    use_rslora=True,
    use_gradient_checkpointing="unsloth",
    random_state = 32,
    loftq_config = None,
  )

  EOS_TOKEN = tokenizer.eos_token
  def formatting_prompt(examples):
    inputs       = examples["before text"]
    outputs      = examples["label"]
    texts = []
    labels = []

    for input_, output_ in zip(inputs, outputs):
      #text = generate_train_template(input_, output)
      text = class_prompt_train(input_, output_)
      text = tokenizer.apply_chat_template(text, tokenize=False, add_generation_prompt=False)
      texts.append(text)
      labels.append(f"{output_}")

    return { "text" : texts}

  full_ds = full_ds.map(formatting_prompt, batched=True)
  print(full_ds["train"].to_pandas()["label"].value_counts())
  print(full_ds["test"].to_pandas()["label"].value_counts())

  trainer = SFTTrainer(
    model = model,
    tokenizer = tokenizer,
    train_dataset = full_ds["train"],
    dataset_text_field = "text",
    max_seq_length = MAX_GEN_LENGTH,
    #data_collator = DataCollatorForSeq2Seq(tokenizer = tokenizer),
    data_collator = DataCollatorForLanguageModeling(tokenizer = tokenizer, mlm=False),
    dataset_num_proc = 2,
    packing = True,
    args = TrainingArguments(
      per_device_train_batch_size = 2,
      gradient_accumulation_steps = 4,
      warmup_steps = 5,
      #max_steps = 60,
      num_train_epochs=1,
      learning_rate = 2e-4,
      fp16 = not is_bfloat16_supported(),
      bf16 = is_bfloat16_supported(),
      logging_steps = 1,
      optim = "adamw_8bit",
      weight_decay = 0.01,
      lr_scheduler_type = "linear",
      seed = 3407,
      output_dir = f"{args.OUTPUT_DIR}",
  ),
  )

  trainer = train_on_responses_only(
    trainer,
    instruction_part = "<|start_header_id|>user<|end_header_id|>\n\n",
    response_part = "<|start_header_id|>assistant<|end_header_id|>\n\n",
  )

  train_results = trainer.train()

  #trainer.log_metrics("train", train_results.metrics)
  #trainer.save_metrics("train", train_results.metrics)

  print("\n\n")
  print(trainer.state.log_history)
  print("\n\n")

  trainer.save_state()

  #merged_model = model.merge_and_unload()
  model.save_pretrained_merged(f"{args.MODEL_SAVE_DIR}", tokenizer, save_method = "merged_16bit")

if __name__ == "__main__":
  main()