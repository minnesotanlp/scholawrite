import os

import torch
import accelerate
from dotenv import load_dotenv
from huggingface_hub import login
from datasets import Dataset, load_dataset
from transformers import TrainingArguments, DataCollatorForSeq2Seq
from trl import SFTConfig, SFTTrainer
from unsloth import FastLanguageModel, is_bfloat16_supported
from unsloth.chat_templates import train_on_responses_only

import args
import taxonomy
from llama3_intention_classifier import load_tokenizer, load_model, get_quantized_model, get_causal_lm_trainer
import dataset_utils
from dataset_utils import add_special_tokens, get_scholawrite_dataset, get_dataset_statistics, get_dataset_from_df, get_intention_inference_instruction_dataset
from classification_utils import generate_train_template

def main():
  print("first")
  load_dotenv()

  print("second")
  HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
  login(token=HUGGINGFACE_TOKEN)

  print("third")
  print(accelerate.Accelerator().device)
  print(accelerate.Accelerator().state)

  print("fourth")
  #if (args.MODEL_TYPE == "llm"):
  #  #tokenizer = load_tokenizer(args.MODEL_NAME)
  #  #model = load_model(args.MODEL_NAME)
  #elif(args.MODEL_TYPE == "small-lm"):
  #  raise Exception("not implemented")
  #else:
  #  raise Exception("not implemented")

  model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/Llama-3.2-1B-Instruct-bnb-4bit",
    max_seq_length=4096,
    load_in_4bit=True,
    dtype=None,
  )
  add_special_tokens(tokenizer)
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
  print(model.print_trainable_parameters())


  EOS_TOKEN = tokenizer.eos_token
  def formatting_prompt(examples):
    inputs       = examples["before_text"]
    outputs      = examples["label"]
    texts = []

    for input_, output in zip(inputs, outputs):
      text = generate_train_template(input_, output)
      text = tokenizer.apply_chat_template(text, tokenize=False, add_generation_prompt=False)
      texts.append(text)
    return { "text" : texts, }

  full_ds = load_dataset("minnesotanlp/scholawrite")
  full_ds = full_ds.map(formatting_prompt, batched=True)

  print(full_ds["train"].to_pandas()["label"].value_counts())
  print(full_ds["test"].to_pandas()["label"].value_counts())

  max_seq_length=5096

  trainer = SFTTrainer(
    model = model,
    tokenizer = tokenizer,
    train_dataset = full_ds["train"],
    dataset_text_field = "text",
    max_seq_length = max_seq_length,
    data_collator = DataCollatorForSeq2Seq(tokenizer = tokenizer),
    dataset_num_proc = 2,
    packing = False,
    args = TrainingArguments(
      per_device_train_batch_size = 2,
      gradient_accumulation_steps = 4,
      warmup_steps = 5,
      max_steps = 60,
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