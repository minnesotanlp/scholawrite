import os

import accelerate
from dotenv import load_dotenv
from huggingface_hub import login

import args
import taxonomy
from llama3_intention_classifier import load_tokenizer, load_model, get_quantized_model, get_causal_lm_trainer
import dataset_utils
from dataset_utils import add_special_tokens, get_scholawrite_dataset, get_dataset_statistics, get_dataset_from_df, get_intention_inference_instruction_dataset

def main():
  load_dotenv()

  HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
  login(token=HUGGINGFACE_TOKEN)

  print(accelerate.Accelerator().device)
  print(accelerate.Accelerator().state)

  if (args.MODEL_TYPE == "llm"):
    tokenizer = load_tokenizer(args.MODEL_NAME)
    model = load_model(args.MODEL_NAME)
  elif(args.MODEL_TYPE == "small-lm"):
    raise Exception("not implemented")
  else:
    raise Exception("not implemented")

  add_special_tokens(model, tokenizer)

  model = get_quantized_model(model)

  dataset_df = get_scholawrite_dataset()
  dataset_df = dataset_utils.preprocess_one_project(dataset_df, args.PROJECT_IDS[0], taxonomy.RELEVANT_CLASSES)
  get_intention_inference_instruction_dataset(dataset_df, tokenizer)
  print(dataset_df.head())
  tokenized_ds = get_dataset_from_df(dataset_df, tokenizer)

  #get_dataset_statistics(dataset)

  #find_max_tokens_length(dataset, tokenizer)

  trainer = get_causal_lm_trainer(model, tokenizer, tokenized_ds)

  ids = tokenized_ds["train"][0]["input_ids"]

  output = model.generate(ids, max_new_tokens=20)
  print(output)
  print(tokenizer.decode(output))

  raise Exception

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