import os

import accelerate
from dotenv import load_dotenv
from huggingface_hub import login
from datasets import load_dataset
from transformers import TrainingArguments, DataCollatorForLanguageModeling
from trl import SFTTrainer
from unsloth import FastLanguageModel, is_bfloat16_supported
from unsloth.chat_templates import train_on_responses_only

import args
from dataset_utils import add_special_tokens
from word_diff import diff_for_llm
from prompt import text_gen_prompt_train

load_dotenv()

def main():

  HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
  login(token=HUGGINGFACE_TOKEN)

  print(accelerate.Accelerator().device)
  print(accelerate.Accelerator().state)

  model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/Meta-Llama-3.1-8B-Instruct-bnb-4bit",
    max_seq_length=4096,
    load_in_4bit=True,
    dtype=None,
  )
  add_special_tokens(tokenizer)
  model.resize_token_embeddings(len(tokenizer), mean_resizing=True)

  model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    lora_alpha=16,
    lora_dropout=0,
    target_modules=["q_proj", "k_proj", "v_proj", "up_proj", "down_proj", "o_proj", "gate_proj"],
    modules_to_save=["embed_tokens", "lm_head"],
    use_rslora=True,
    use_gradient_checkpointing="unsloth",
    random_state = 32,
    loftq_config = None,
  )
  print("trainable parameters", model.print_trainable_parameters())


  def formatting_prompt(examples):
    bt = examples["before text"]
    at = examples["after text"]
    wi = examples["label"]

    texts = []
    for bt_, wi_, at_ in zip(bt, wi, at):
      at_ = diff_for_llm(bt_, at_)
      text = text_gen_prompt_train(bt_, wi_, at_)
      text = tokenizer.apply_chat_template(text, tokenize=False, add_generation_prompt=False)
      texts.append(text)
    return { "text" : texts, }

  full_ds = load_dataset("minnesotanlp/scholawrite", revision="anonymous_data")
  full_ds = full_ds.map(formatting_prompt, batched=True, num_proc=16)

  max_seq_length=5096

  trainer=SFTTrainer(
      model=model,
      tokenizer=tokenizer,
      train_dataset=full_ds["train"],
      eval_dataset=full_ds["test"],
      dataset_text_field="text",
      max_seq_length=max_seq_length,
      data_collator = DataCollatorForLanguageModeling(tokenizer = tokenizer, mlm=False),
      dataset_num_proc=16,
      args=TrainingArguments(
          learning_rate=3e-4,
          lr_scheduler_type="linear",
          per_device_train_batch_size=1,
          gradient_accumulation_steps=4,
          num_train_epochs=1,
          fp16=not is_bfloat16_supported(),
          bf16=is_bfloat16_supported(),
          logging_steps=10,
          save_strategy="no",
          optim="adamw_8bit",
          weight_decay=0.01,
          warmup_steps=10,
          output_dir=f"{args.OUTPUT_DIR}",
          seed=0,
      ),
  )

  trainer = train_on_responses_only(
    trainer,
    instruction_part = "<|start_header_id|>user<|end_header_id|>\n\n",
    response_part = "<|start_header_id|>assistant<|end_header_id|>\n\n",
  )

  train_results = trainer.train()

  trainer.log_metrics("train", train_results.metrics)
  trainer.save_metrics("train", train_results.metrics)

  print("\n\n")
  print(trainer.state.log_history)
  print("\n\n")

  trainer.save_state()

  model.save_pretrained_merged(f"{args.MODEL_SAVE_DIR}", tokenizer, save_method = "merged_16bit")

if __name__ == "__main__":
  main()