"""

arguments for the model fine-tuning

msi interactive gpu session:
srun -N 1 --ntasks-per-node=1 --mem-per-cpu=1gb -t 1:00:00 -p interactive-gpu --gres=gpu:a40:1 --pty bash

"""

import os
from datetime import datetime

#MODEL_TYPE = "small-lm"
MODEL_TYPE = "llm"

#MODEL_NAME = "bert-base-uncased"
#MODEL_NAME = "FacebookAI/roberta-base"
#MODEL_NAME = "meta-llama/Meta-Llama-3-8B"
#MODEL_NAME = "meta-llama/Llama-3.2-1B"
#MODEL_NAME = "unsloth/Llama-3.2-1B-bnb-4bit"
MODEL_NAME = "unsloth/Llama-3.2-3B-bnb-4bit"

#TIMESTAMP = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
TIMESTAMP = ""

PURPOSE = "PREDICTION_nov13"

BASE_DIR = "/workspace"                    # DOCKER
#BASE_DIR = "/users/0/volko032/scholawrite" # MSI

OUTPUT_DIR = f"{BASE_DIR}/results/{MODEL_NAME}_run_{TIMESTAMP}_{PURPOSE}"
#OUTPUT_DIR = f"/users/0/volko032/scholawrite/results/{MODEL_NAME}_run_{TIMESTAMP}_{PURPOSE}"
LOG_DIR = f"{OUTPUT_DIR}/log"
MEDIA_DIR = f"{OUTPUT_DIR}/media"
MODEL_SAVE_DIR = f"{OUTPUT_DIR}/model_save"

if False:
  os.makedirs(OUTPUT_DIR, mode = 0o777, exist_ok = True) 
  os.makedirs(MEDIA_DIR, mode = 0o777, exist_ok = True) 
  os.makedirs(MODEL_SAVE_DIR, mode = 0o777, exist_ok = True) 

print("outputdir", OUTPUT_DIR)

PROJECT_IDS = [
  "6500d748909490ecba83e811",  # Debarati's project part 1, Done
  "6578ec8845504beacf9d3dc7",  # Debarati's project part 2, Done
  "654682f220e7d557c7e67cff",  # Anna's project, Done
  "656a440644dec9f71f2dee44",  # Zae's project, Done
  "640e22cae918523bcee8ca5e", # karin's project, Done
  #"656fadd102ae94a7686aae62"  # Artifact paper, Not done
]