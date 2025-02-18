# ScholaWrite: A Dataset of End-to-End Scholarly Writing Process

## Abstract
Writing is a cognitively active task involving continuous decision-making, heavy use of working memory, and frequent switching between multiple activities.
Scholarly writing is particularly complex as it requires authors to coordinate many pieces of multiform knowledge while meeting high academic standards.
To understand writers' cognitive thinking process, one should fully decode the *end-to-end writing data* (from scratch to final manuscript) and understand their complex cognitive mechanisms in scientific writing.
We introduce <span style="font-variant: small-caps;">ScholaWrite</span> dataset, the first-of-its-kind keystroke logs of an end-to-end scholarly writing process, with thorough annotations of cognitive writing intentions behind each keystroke. 
Our dataset includes $\LaTeX$-based keystroke data from five preprints with nearly 62K total text changes and annotations across 4 months of paper writing.
Our dataset shows promising usability and applications for the future development of AI writing assistants for the research environment, which necessitate complex methods beyond LLM prompting, and supports the cognitive thinking process of scientists.


## About
This branch contains following folders:
- `scholawrite_system`: ScholaWrite system which includes data collection backend, admin page, and annotation page.
- `scholawrite_finetune`: Fine-tuning scripts of BERT, RoBERTa, and Llama-8b-instruct on our dataset.
- `gpt4o`: Scripts for running GPT-4o on iterative writing and intention prediction.
- `meta_inference`: Scripts for running Llama-8b-instruct baseline model on iterative writing and intention prediction.
- `eval_tool`: Webpage for visualizing Llama-8b-instruct (baseline) and Llama-8b-SW iterative writing output for human evaluation.
- `analysis`: Scripts for computing consine similarity between seed documents and final outputs of iterative writing, lexical diversity of final outputs from iterative writing, f1 scores in intention prediction task, and intention diversity/converage in the iterative writing.

## Run ScholaWrite System

### Step 1, setup the MongoDB
1. Go to this [site](https://www.mongodb.com/docs/manual/administration/install-community/) to download and install the MongoDB on your computer.
2. Go to this [site](https://www.mongodb.com/try/download/compass) to download the MongoDB Compass, it provides a user friendly GUI that allows you to view/find/manage the documents in the database. MongoDB Compass also provide mongoDB Shell feature.
3. Install the [Database Tools](https://www.mongodb.com/docs/database-tools/installation/installation/#installing-the-database-tools) based on your OS so that you can backup and restore your database.
4. Run the MongoDB on default port 27017.
5. The database named `flask_db` and collection `activity` inside it will be created once you run the ScholaWrite System.

### Step 2, setup the Google OAuth

1. Make sure you have a Google Cloud [project](https://developers.google.com/workspace/guides/create-project).
2. Follow the [steps](https://developers.google.com/workspace/guides/create-credentials#oauth-client-id) to create an OAuth client for a **Desktop app**.
3. Download the OAuth client file you just created and rename it to `sheet_credential.json`.
4. Place it in any folder you want.
5. Replace lines 12 and 13 in `/scholwrite_system/docker-compose.yml` with the following:
   ```yaml
   volumes:
       - <folder path you put the sheet_credential.json>/sheet_credential.json:/usr/local/src/scholawrite/flaskapp/sheet_credential.json
       - <folder path you put the token.json>/google_OAuth2/token.json:/usr/local/src/scholawrite/flaskapp/token.json
   ```

### Step 3, setup your Google Sheet

1. Make sure you have a Google Sheet.
2. Add all Overleaf project IDs you want the system to monitor. The IDs should be on consecutive rows in the same column (e.g., `A1:A9`).
3. Go to line 21 of `scholawrite_system/App.py`.
4. Replace `SAMPLE_SPREADSHEET_ID` with the ID of your Google Sheet. The ID is in the URL of your Google Sheet: `https://docs.google.com/spreadsheets/d/<SAMPLE_SPREADSHEET_ID>/edit?gid=0#gid=0`.
5. Go to line 23 of `scholawrite_system/App.py`.
6. Replace `SAMPLE_RANGE_NAME` with the actual range in the Google Sheet where you stored the Overleaf project IDs.

### Step 4, setup Ngrok

1. You need either:
   - One Ngrok account that supports **3 Static Domains** and **3 Secure Tunnel Agents**, or
   - Three Ngrok accounts that each support **1 Static Domain** and **1 Secure Tunnel Agent**.
2. Go to the [Ngrok dashboard](https://dashboard.ngrok.com/get-started/your-authtoken) and copy your AuthToken.
3. Create three configuration files in the `scholawrite_system` folder named `ngrok_admin.yml`, `ngrok_annotation.yml`, and `ngrok_schola.yml`.
4. Paste your AuthToken(s) into these files in the following format:
   ```yaml
   version: 2
   authtoken: <Your AuthToken>
   ```
5. Create three [domains](https://dashboard.ngrok.com/domains).
6. Paste the domains into the `command` lines on lines 36, 63, and 90 in `/scholwrite_system/docker-compose.yml`. For example:
   ```yaml
   command: ["ngrok", "http", "annotation:5100", "--host-header=annotation:5100", "--domain=<your domain>", "--log=stdout", "--log-level=debug"]
   ```

### Now you are ready to go!
Run the following command:
```bash
docker-compose up
```
The data collection backend, admin page, and annotation page will be running and assesible to the public through Ngrok.

---

## Setup the Extension

### Step 1, update URL to server

1. Copy the domain from the `command` on line 36 in `scholawrite_system/docker-compose.yml`.
2. Paste it into:
   - Line 3 of `scholawrite_system/extention/background.js`
   - Line 5 of `scholawrite_system/extention/popup.js`

### Step 2, install and Run the Extension

1. Open your browser and go to `chrome://extensions`.
2. Enable **Developer Mode** at the top-right corner of the page.
3. Click **Load unpacked** and navigate to the `scholawrite_system` folder.
4. Select the `extension` folder.
5. Once the extension is loaded:
   - Open another Chrome tab and go to your Overleaf project page.
   - If already open, refresh the page.
6. Click the puzzle icon at the top-right corner of your browser, and the `S` logo will appear.
7. Click the `S` logo to show the extension UI.
8. Log in or register, then toggle on **Record writer actions**.

**Note:** Due to Overleaf UI updates, the Chrome extension can no longer record writer actions or perform the AI paraphrase feature.

---

## Run Eval Tool

### Step 1, setup Ngrok

1. You need one Ngrok account that supports **1 Static Domain** and **1 Secure Tunnel Agent**.
2. Go to the [Ngrok dashboard](https://dashboard.ngrok.com/get-started/your-authtoken) and copy your AuthToken.
3. Create a configuration file in the `eval_tool` folder named `ngrok.yml`.
4. Paste your AuthToken into the file in the following format:
   ```yaml
   version: 2
   authtoken: <Your AuthToken>
   ```
5. Create one [domain](https://dashboard.ngrok.com/domains).
6. Paste the domain into the `command` line in `/eval_tool/run_eval_app.sh`:
   ```bash
   tmux new-session -d -s eval_ngrok "ngrok --config ./ngrok.yml http --url=<your domain> 12345"
   ```

### Step 2, run the Docker

1. Navigate to the `eval_tool` folder.
2. Run:
   ```bash
   docker-compose up -d
   ```
3. After the container is created, run:
   ```bash
   docker exec -it scholawrite_eval bash
   ```
4. Inside the container, run:
   ```bash
   ./run_eval_app.sh
   ```
5. Go to the domain you pasted into `/eval_tool/run_eval_app.sh` using your browser.

---

## Run Fine-Tuning

The fine-tuning uses **Unsloth** and **QLoRA**. Ensure your GPU has at least **16GB VRAM**.

### Step 1: Set Up the Environment
1. Navigate to the root folder of `ScholaWrite-Public`.
2. Create an `.env` file with following content
    ```bash
    HUGGINGFACE_TOKEN="<Your Hugging Face access token>"
    OPEN_AI_API="<Your OpenAI API key>"
    ```
3. Create a Docker container for fine-tuning and inference:
    ```bash
    docker run --name scholawrite_container_2 --gpus all -dt -v ./:/workspace --ipc=host pytorch/pytorch:2.4.1-cuda12.1-cudnn9-devel bash
    ```
4. Access the Docker container:
    ```bash
    docker exec -it scholawrite_container_2 bash
    ```
5. Install required Python packages:
    ```bash
    pip install accelerate python-dotenv huggingface-hub datasets transformers trl unsloth diff_match_patch
    ```


### Step 2: Choose a Model for Fine-Tuning

1. Inside the Docker container, navigate to the `scholawrite_finetune` folder.
2. Select the appropriate folder based on the model you want to fine-tune:
    - `bert_finetune`: For fine-tuning `bert-base-uncased` or `FacebookAI/roberta-base` on a classification task.
    - `llama8b_scholawrite_finetune`: For fine-tuning `unsloth/Meta-Llama-3.2-8B-Instruct-bnb-4bit` on classification or iterative writing tasks.


### Step 3: Start Fine-Tuning

#### For `llama8b_scholawrite_finetune`

- **Iterative Writing**:
  1. Open `args.py` and set `PURPOSE = "WRITING"`.
  2. Run the fine-tuning script:
      ```bash
      python3 train_writing.py
      ```

- **Classification**:
  1. Open `args.py` and set `PURPOSE = "CLASS"`.
  2. Run the fine-tuning script:
      ```bash
      python3 train_classifier.py
      ```

#### For `bert_finetune`
- **Classification**:
    1. Run the fine-tuning script:
        ```bash
        python3 small_model_classifier.py
        ```

After fine-tuning, the fine-tuned model will be stored in the `results` folder in the root directory of `ScholaWrite-Public`.

---

## Inference

### Step 1: Set Up the Environment

Ensure you are inside the `scholawrite_container_2` Docker container.

- **If already running**:
    ```bash
    docker exec -it scholawrite_container_2 bash
    ```
- **If not running**:

  Follow the setup instructions in the [Environment Setup Section](#step-1-set-up-the-environment).


### Step 2: Choose a Model for Inference

Navigate to the appropriate folder inside the Docker container.

- **`scholawrite_finetune`**:
    - `bert_finetune`: For running classification on fine-tuned `bert-base-uncased` or `FacebookAI/roberta-base`.
    - `llama8b_scholawrite_finetune`: For running classification or iterative writing on fine-tuned `unsloth/Meta-Llama-3.2-8B-Instruct-bnb-4bit`.

- **`meta_inference`**:
    - `llama8b_meta_instruction`: For running classification or iterative writing baseline `unsloth/Llama-3.2-8B-Instruct-bnb-4bit`.


### Step 3: Start Inference
#### For `scholawrite_finetune/llama8b_scholawrite_finetune`
- **Iterative Writing**:  
    1. Ensure the model name on lines 65 and 80 of `iterative_writing.py` matches the path to the model or its name on Hugging Face.
    2. On line 15 of `iterative_writing.py`, specify a unique `output_folder_name` to avoid overwriting existing outputs.
    3. Run the script:
        ```bash
        python3 iterative_writing.py
        ```
    4. Outputs will be saved in `output_folder_name/seed name/generation` and `output_folder_name/seed name/intention` folders under the `ScholaWrite-Public` root directory.
        - `seed name`: filenames of seed documents (please refer to `ScholaWrite-Public/seeds`), here are all possible seed names: seed1, seed2, seed3, and seed4.
        - `output_folder_name/seed name/generation`: Stores the model's writing output, with one text file per iteration (e.g., 100 iterations result in 100 text files).
        - `output_folder_name/seed name/intention`: Stores the model's intentions corresponding to each writing output, with one text file per iteration (e.g., 100 iterations result in 100 text files).

- **Classification**:
  1. Ensure the model name on line 40 of `classification.py` matches the path to the model or its name on Hugging Face.
  2. Run the script:
      ```bash
      python3 classification.py
      ```
  3. A CSV file with classification results will be generated in the current directory.
  4. True label is in the column 'label' and predicted label is in the column 'predicted'

#### For `scholawrite_finetune/bert_finetune`
- **Classification**:
    1. Run the script:
        ```bash
        python3 small_model_inference.py
        ```
    2. A CSV file with classification results will be generated in the current directory.
    3. True label is in the column 'label' and predicted label is in the column 'predicted_label'

---
## Code Contributors
[Linghe Wang](https://github.com/Linghe-Wang), [Ross Volkov](https://github.com/rvolkov1), [Minhwa Lee](https://github.com/mimn97)

## BibTex
```
@misc{wang2025scholawritedatasetendtoendscholarly,
      title={ScholaWrite: A Dataset of End-to-End Scholarly Writing Process},
      author={Linghe Wang and Minhwa Lee and Ross Volkov and Luan Tuyen Chau and Dongyeop Kang},
      year={2025},
      eprint={2502.02904},
      archivePrefix={arXiv},
      primaryClass={cs.CL},
      url={https://arxiv.org/abs/2502.02904},
}
```

