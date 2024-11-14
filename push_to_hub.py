import os
from transformers import LlamaForCausalLM, AutoTokenizer
from dotenv import load_dotenv
load_dotenv()

from huggingface_hub import login
login(os.getenv("HUGGINGFACE_TOKEN"))


model_name = "/workspace/results/unsloth/Llama-3.2-3B-bnb-4bit_run__TEXT_PREDICTION_NEW_LABEL/model_save"

model = LlamaForCausalLM.from_pretrained(
    model_name
)

tokenizer = AutoTokenizer.from_pretrained(model_name)

model.push_to_hub("minnesotanlp/scholawrite-llama3.2")
tokenizer.push_to_hub("minnesotanlp/scholawrite-llama3.2")