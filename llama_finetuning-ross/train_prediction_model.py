import os

import accelerate
import torch
from dotenv import load_dotenv
from huggingface_hub import login
from datasets import Dataset, load_dataset
from transformers import TrainingArguments, DataCollatorForLanguageModeling
from trl import SFTConfig, SFTTrainer
from unsloth import FastLanguageModel, is_bfloat16_supported

import args
#import taxonomy
#from llama3_intention_classifier import load_tokenizer, load_model, get_quantized_model, get_causal_lm_trainer
import dataset_utils
from dataset_utils import add_special_tokens, get_scholawrite_dataset, get_dataset_statistics, get_dataset_from_df, get_writing_prediction_instruction_dataset
from word_diff import diff_for_llm
from prompt import text_gen_prompt_train

def main():
  load_dotenv()

  HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
  login(token=HUGGINGFACE_TOKEN)

  print(accelerate.Accelerator().device)
  print(accelerate.Accelerator().state)

  model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/Llama-3.2-3B-Instruct-bnb-4bit",
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
  print("trainable parameters", model.print_trainable_parameters())

  #def generate_train_template(before_text, writing_intention, after_text):
  #  prompt = f"""Given an excerpt from a research paper and a scholarly writing intention, revise or add to the text to fulfill this writing intention. ### exerpt: {before_text} ### Writing intention: {writing_intention}"""
  #  return [
  #    {"role": "user", "content": prompt},
  #    {"role": "assistant", "content": after_text}
  #  ]

  def formatting_prompt(examples):
    bt = examples["before text"]
    at = examples["after text"]
    wi = examples["label"]

    texts = []
    for bt_, wi_, at_ in zip(bt, wi, at):
      at_ = diff_for_llm(bt_, at_)
      #text = generate_train_template(bt_, wi_, at_)
      text = text_gen_prompt_train(bt_, wi_, at_)
      text = tokenizer.apply_chat_template(text, tokenize=False, add_generation_prompt=False)
      texts.append(text)
    return { "text" : texts, }

  full_ds = load_dataset("minnesotanlp/scholawrite", revision="anonymous_data")
  full_ds = full_ds.map(formatting_prompt, batched=True)

  max_seq_length=5096

  trainer=SFTTrainer(
      model=model,
      tokenizer=tokenizer,
      train_dataset=full_ds["train"],
      eval_dataset=full_ds["test"],
      dataset_text_field="text",
      max_seq_length=max_seq_length,
    data_collator = DataCollatorForLanguageModeling(tokenizer = tokenizer, mlm=False),
      dataset_num_proc=2,
      packing=True,
      args=TrainingArguments(
          learning_rate=3e-4,
          lr_scheduler_type="linear",
          per_device_train_batch_size=1,
          gradient_accumulation_steps=4,
          num_train_epochs=1,
          #num_train_epochs=1,
          fp16=not is_bfloat16_supported(),
          bf16=is_bfloat16_supported(),
          logging_steps=1,
          save_strategy="steps",
          #save_total_limit=3,
          optim="adamw_8bit",
          weight_decay=0.01,
          warmup_steps=10,
          output_dir=f"{args.OUTPUT_DIR}",
          seed=0,
      ),
  )

  train_results = trainer.train()

  trainer.log_metrics("train", train_results.metrics)
  trainer.save_metrics("train", train_results.metrics)

  print("\n\n")
  print(trainer.state.log_history)
  print("\n\n")

  trainer.save_state()

  #merged_model = model.merge_and_unload()
  #merged_model.save_pretrained(f"{args.MODEL_SAVE_DIR}", safe_serialization=True)
  model.save_pretrained_merged(f"{args.MODEL_SAVE_DIR}", tokenizer, save_method = "merged_16bit")

if __name__ == "__main__":
  main()