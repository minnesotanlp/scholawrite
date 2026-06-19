<div align="center">


## ScholaWrite: A Dataset of End-to-End Scholarly Writing Process


**Khanh Chi Le · Linghe Wang · Minhwa Lee · Ross Volkov · Luan Tuyen Chau · Dongyeop Kang**  
University of Minnesota

<p>
  <a href="https://arxiv.org/abs/2502.02904"><img alt="arXiv" src="https://img.shields.io/badge/arXiv-2605.00557-b31b1b.svg"></a>
  <a href="https://minnesotanlp.github.io/scholawrite/"><img alt="Website" src="https://img.shields.io/badge/Website-ScholaWrite-2f7d6b.svg"></a>
  <a href="https://huggingface.co/datasets/minnesotanlp/scholawrite"><img alt="Code" src="https://img.shields.io/badge/Code-GitHub-24292f.svg"></a>
  <a href="https://huggingface.co/datasets/minnesotanlp/scholawrite"><img alt="Hugging Face" src="https://img.shields.io/badge/🤗%20Hugging%20Face-Dataset-ffcc4d.svg"></a>
</p>

</div>

## Abstract

Writing is a cognitively demanding activity that requires constant decision-making, heavy reliance on working memory, and frequent shifts between tasks of different goals. To build writing assistants that truly align with writers’ cognition, it is necessary to capture and analyze the complete thought process behind how writers transform ideas into final texts. We present **ScholaWrite**, the first dataset of end-to-end scholarly writing, tracing the multi-month journey from initial drafts to final manuscripts. The dataset traces nearly 62K LATEX-based edits from five computer science preprints over four months and is enriched with fine-grained annotations of cognitive writing intentions. We demonstrate the value of ScholaWrite through three complementary contributions: 
- (1) analysis of real-world writing behavior reveals that scholarly writing is highly non-linear and multiintentional, blending rapid drafting bursts with cognitively sustained writing sessions; 
- (2) evaluations of current large language models show that they struggle to provide meaningful support throughout the human writing process; and
- (3) models finetuned on SCHOLAWRITE demonstrate improved alignment with human writing workflows. SCHOLAWRITE underscores the value of capturing scientists’ cognitive writing process and provides actionable insights and resources for the development of future writing assistants.

## Repository Structure

| Directory | Description |
|---|---|
| `scholawrite_system/` | Data collection backend, admin page, annotation page, and Chrome extension |
| `scholawrite_finetune/` | Fine-tuning scripts for BERT, RoBERTa, and Llama-8B-Instruct |
| `gpt4o/` | GPT-4o inference for iterative writing and intention prediction |
| `meta_inference/` | Llama-8B-Instruct baseline inference |
| `experiments/` | Notebooks for LLM output generation and evaluation (session-level and intent-conditioned), research question analysis, and zero-shot vs. ScholaWrite fine-tuned model comparisons |
| `eval_tool/` | Web interface for human evaluation of model outputs |
| `analysis/` | Evaluation metrics, cosine similarity, lexical diversity, and figure generation |
| `augmented/` | AI-generated content detection benchmarks (ScholaWrite-Augmented) |
| `seeds/` | Seed documents for iterative writing experiments |
| `outputs/` | Pre-computed inference outputs from all models |

## Getting Started

### Prerequisites

- Docker & Docker Compose
- GPU with >= 16GB VRAM (for fine-tuning/inference)
- Python 3.8+

### Environment Setup

Create an `.env` file in the project root:

```bash
HUGGINGFACE_TOKEN="<Your Hugging Face access token>"
OPEN_AI_API="<Your OpenAI API key>"
```

Create a Docker container for fine-tuning and inference:

```bash
docker run --name scholawrite --gpus all -dt -v ./:/workspace --ipc=host pytorch/pytorch:2.4.1-cuda12.1-cudnn9-devel bash
docker exec -it scholawrite bash
pip install accelerate python-dotenv huggingface-hub datasets transformers trl unsloth diff_match_patch
```

---

## ScholaWrite System

The data collection system uses Flask + MongoDB with a Chrome extension for Overleaf.

### 1. MongoDB

1. Install [MongoDB Community Edition](https://www.mongodb.com/docs/manual/administration/install-community/) and [MongoDB Compass](https://www.mongodb.com/try/download/compass).
2. Install [Database Tools](https://www.mongodb.com/docs/database-tools/installation/installation/#installing-the-database-tools).
3. Run MongoDB on the default port (27017). The `flask_db` database and `activity` collection are created automatically.

### 2. Google OAuth

1. Create a [Google Cloud project](https://developers.google.com/workspace/guides/create-project) and an [OAuth client](https://developers.google.com/workspace/guides/create-credentials#oauth-client-id) for a **Desktop app**.
2. Download the credentials file, rename it to `sheet_credential.json`.
3. Update the volume paths in `scholawrite_system/docker-compose.yml` (lines 12-13):
   ```yaml
   volumes:
     - <path>/sheet_credential.json:/usr/local/src/scholawrite/flaskapp/sheet_credential.json
     - <path>/token.json:/usr/local/src/scholawrite/flaskapp/token.json
   ```

### 3. Google Sheet

1. Add Overleaf project IDs to consecutive rows in a Google Sheet column.
2. In `scholawrite_system/flaskapp/App.py`, update:
   - Line 22: `SAMPLE_SPREADSHEET_ID` with your Sheet ID
   - Line 23: `SAMPLE_RANGE_NAME` with your cell range

### 4. Ngrok

1. Get 3 static domains and auth tokens from [Ngrok](https://dashboard.ngrok.com/).
2. Create `ngrok_admin.yml`, `ngrok_annotation.yml`, and `ngrok_schola.yml` in `scholawrite_system/`:
   ```yaml
   version: 2
   authtoken: <Your AuthToken>
   ```
3. Paste your domains into `docker-compose.yml` on lines 36, 63, and 90.

### 5. Launch

```bash
cd scholawrite_system
docker-compose up
```

### Chrome Extension

1. Update the server URL in `scholawrite_system/extension/background.js` (line 3) and `popup.js` (line 5).
2. In Chrome, go to `chrome://extensions` → enable **Developer Mode** → **Load unpacked** → select the `extension/` folder.

> **Note:** Due to Overleaf UI updates, the Chrome extension can no longer record writer actions or perform AI paraphrase.

---

## Fine-Tuning

Inside the Docker container, navigate to `scholawrite_finetune/`:

**Llama-8B** (`llama8b_scholawrite_finetune/`):
```bash
# Iterative writing — set PURPOSE = "WRITING" in args.py
python3 train_writing.py

# Classification — set PURPOSE = "CLASS" in args.py
python3 train_classifier.py
```

**BERT / RoBERTa** (`bert_finetune/`):
```bash
python3 small_model_classifier.py
```

Fine-tuned models are saved to `results/` in the project root.

---

## Inference

### Fine-tuned Llama-8B (`scholawrite_finetune/llama8b_scholawrite_finetune/`)

```bash
# Iterative writing — update model path in iterative_writing.py (lines 65, 80)
python3 iterative_writing.py

# Classification — update model path in classification.py (line 40)
python3 classification.py
```

### Baseline Llama-8B (`meta_inference/llama8b_meta_instruction/`)

```bash
python3 iterative_writing.py
python3 classification.py
```

### GPT-4o (`gpt4o/`)

```bash
python3 iterative_writing.py
python3 classification.py
```

Output structure: `<output_dir>/<seed>/generation/` and `<output_dir>/<seed>/intention/` (100 iterations each).

---

## Eval Tool

1. Set up Ngrok with 1 static domain. Create `eval_tool/ngrok.yml` with your auth token.
2. Update the domain in `eval_tool/run_eval_app.sh`.
3. Run:
   ```bash
   cd eval_tool
   docker-compose up -d
   docker exec -it scholawrite_eval bash
   ./run_eval_app.sh
   ```

---

## Citation

```bibtex
@inproceedings{le2026scholawrite,
  title={ScholaWrite: A Dataset of End-to-End Scholarly Writing Process},
  author={Khanh Chi Le and Linghe Wang and Minhwa Lee and Ross Volkov and Luan Tuyen Chau and Dongyeop Kang},
  year={2026},
  booktitle={Proceedings of the 64rd Annual Meeting of the Association for Computational Linguistics (ACL 2026)},
  note={To appear},
  url={https://arxiv.org/abs/2502.02904},
}
```

## Code Contributors

[Linghe Wang](https://github.com/Linghe-Wang), [Ross Volkov](https://github.com/rvolkov1), [Minhwa Lee](https://github.com/mimn97), [Khanh Chi Le](https://github.com/chile2706)

## License

This project is licensed under the [MIT License](LICENSE).
