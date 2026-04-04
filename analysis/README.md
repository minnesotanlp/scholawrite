# Analysis

Scripts for computing evaluation metrics and generating figures for the paper.

## Setup

Uses the same Docker environment as fine-tuning (see root [README](../README.md#environment-setup)).

## Scripts

| Script | Description |
|---|---|
| `classification_stats.py` | Computes accuracy, F1 (macro/micro), and generates confusion matrices |
| `cosine_similar.py` | Computes cosine similarity between seed documents and final outputs |
| `lexical_diverse.py` | Calculates lexical diversity (unique token ratio) of generated text |
| `inference_statistics.py` | Computes intention diversity and coverage statistics |
| `human_eval_results.py` | Generates bar charts for human evaluation results |
| `analysis.ipynb` | Exploratory analysis notebook |

## Usage

```bash
cd analysis
python classification_stats.py
python cosine_similar.py
python lexical_diverse.py
python inference_statistics.py
python human_eval_results.py
```
