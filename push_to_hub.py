import os
from unsloth import FastLanguageModel
from transformers import LlamaForCausalLM, AutoTokenizer
from dotenv import load_dotenv
load_dotenv()

from huggingface_hub import login
login(os.getenv("HUGGINGFACE_TOKEN"))

model_name = "/workspace/results/unsloth/Llama-3.2-3B-bnb-4bit_run__LLAMA_3B_CLASSIFIER/model_save"

model, tokenizer = FastLanguageModel.from_pretrained(
  model_name=model_name,
  max_seq_length=4096,
  load_in_4bit=True,
  dtype=None
)

model.push_to_hub("minnesotanlp/scholawrite-llama3.2-3b-classifier")
tokenizer.push_to_hub("minnesotanlp/scholawrite-llama3.2-3b-classifier")