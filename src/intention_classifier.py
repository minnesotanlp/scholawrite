import os

import accelerate
import torch
from dotenv import load_dotenv
from huggingface_hub import login
from datasets import Dataset
from transformers import TrainingArguments
from trl import SFTConfig, SFTTrainer
from unsloth import FastLanguageModel, is_bfloat16_supported

import args
import taxonomy
from llama3_intention_classifier import load_tokenizer, load_model, get_quantized_model, get_causal_lm_trainer
import dataset_utils
from dataset_utils import add_special_tokens, get_scholawrite_dataset, get_dataset_statistics, get_dataset_from_df, get_intention_inference_instruction_dataset

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
    model_name="unsloth/Llama-3.2-1B-bnb-4bit",
    max_seq_length=4096,
    load_in_4bit=True,
    dtype=None,
  )
  add_special_tokens(model, tokenizer)

  #model = get_quantized_model(model)

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

  dataset_df = get_scholawrite_dataset()
  dataset_df = dataset_utils.preprocess_many_projects(dataset_df, args.PROJECT_IDS, taxonomy.RELEVANT_CLASSES)
  #dataset_df = dataset_df.iloc[0:100]

  print(dataset_df.head())
  #get_intention_inference_instruction_dataset(dataset_df, tokenizer)
  #print(dataset_df.head())
  #tokenized_ds = get_dataset_from_df(dataset_df, tokenizer)

  data_prompt = """Identify the most likely next writing intention of a graduate researcher when editing the following text.

  ### Input:
  {}

  ### Response:
  {}"""

  EOS_TOKEN = tokenizer.eos_token
  def formatting_prompt(examples):
      inputs       = examples["before_text"]
      outputs      = examples["label"]
      texts = []
      for input_, output in zip(inputs, outputs):
          text = data_prompt.format(input_, output) + EOS_TOKEN
          texts.append(text)
      return { "text" : texts, }

  full_ds = Dataset.from_pandas(dataset_df)
  full_ds = full_ds.map(formatting_prompt, batched=True)
  full_ds = full_ds.train_test_split(test_size=0.2)

  print("training_data", full_ds)

  max_seq_length=5096

  trainer=SFTTrainer(
      model=model,
      tokenizer=tokenizer,
      train_dataset=full_ds["train"],
      eval_dataset=full_ds["test"],
      dataset_text_field="text",
      max_seq_length=max_seq_length,
      dataset_num_proc=2,
      packing=True,
      args=TrainingArguments(
          learning_rate=3e-4,
          lr_scheduler_type="linear",
          per_device_train_batch_size=1,
          gradient_accumulation_steps=4,
          num_train_epochs=40,
          fp16=not is_bfloat16_supported(),
          bf16=is_bfloat16_supported(),
          logging_steps=1,
          optim="adamw_8bit",
          weight_decay=0.01,
          warmup_steps=10,
          output_dir="output",
          seed=0,
      ),
  )
  print(torch.cuda.memory_summary(device=None, abbreviated=False))
  trainer.train()

  raise Exception

  #get_dataset_statistics(dataset)

  #find_max_tokens_length(dataset, tokenizer)

  #trainer = get_causal_lm_trainer(model, tokenizer, tokenized_ds)

  #ids = tokenized_ds["train"][0]["input_ids"]
  #print("ids:", ids)
  #output = model.generate(ids, max_new_tokens=20)
  #print(output)
  #print(tokenizer.decode(output))

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