# Process Attestation Analysis

Empirical validation that cognitive process signatures retain discriminative
power in keystroke timing data, using ScholaWrite and the KLiCKe corpus.

## Quick Start

```bash
pip install -r requirements.txt
python run_analysis.py
```

## Pipeline

The script runs 7 stages:

1. **Environment check** -- Python, packages, data availability
2. **ScholaWrite analysis** -- IKI distributions, Shannon entropy, Cognitive
   Load Correlation (CLC), composition vs. transcription discrimination
3. **KLiCKe corpus analysis** -- population-level validation across 4,971 writers
4. **Adversarial retype simulation** -- 4 attack types (constant-rate, IID,
   cross-writer, Markov-chain)
5. **ROC classification** -- leave-one-writer-out logistic regression
6. **Effect sizes and figures** -- Cohen's d, Glass's delta, Cliff's delta
7. **Summary report** -- consolidated findings vs. paper claims

ScholaWrite loads from HuggingFace automatically. KLiCKe is optional and
can be auto-downloaded from Kaggle (requires account).

## Key Results

| Metric | Result | 
|--------|--------|
| ScholaWrite IKI entropy | 10.44 bits/event |
| KLiCKe CLC Cohen's d (composition vs. transcription) | 1.82 (large) |
| Classification AUC (all attacks combined) | 0.83 |
| KLiCKe population | 4,971 writers, 16.8M IKIs |

## Author

David Condrey (david@writerslogic.com), WritersLogic Inc.
