import os
from datetime import datetime

MODEL_NAME = "unsloth/Llama-3.1-8B-bnb-4bit"

TIMESTAMP = datetime.now().strftime('%m-%d-%H')

PURPOSE = "WRITING"

BASE_DIR = "/workspace"

OUTPUT_DIR = f"{BASE_DIR}/results/{MODEL_NAME}_run_{TIMESTAMP}_{PURPOSE}"
LOG_DIR = f"{OUTPUT_DIR}/log"
MEDIA_DIR = f"{OUTPUT_DIR}/media"
MODEL_SAVE_DIR = f"{OUTPUT_DIR}/model_save"

if False:
  os.makedirs(OUTPUT_DIR, mode = 0o777, exist_ok = True) 
  os.makedirs(MEDIA_DIR, mode = 0o777, exist_ok = True) 
  os.makedirs(MODEL_SAVE_DIR, mode = 0o777, exist_ok = True) 

print("outputdir", OUTPUT_DIR)
