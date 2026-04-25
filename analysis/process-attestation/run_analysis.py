#!/usr/bin/env python3
"""
Cognitive Process Signatures in Keystroke Data: Empirical Validation
====================================================================
Single-script pipeline demonstrating that cognitive process signatures
retain discriminative power in keystroke timing data.

Prepared for Prof. Dongyeop Kang (University of Minnesota, MinnesotaNLP)
as a concrete, reproducible demo of specific signals from ScholaWrite
that still retain discriminative power in practice.

Pipeline stages:
  1. Environment check
  2. ScholaWrite analysis (HuggingFace; always runs)
  3. KLiCKe corpus analysis (local CSV; optional)
  4. Adversarial retype simulation (requires KLiCKe)
  5. ROC classification (requires Stage 4 output)
  6. Effect sizes and figures (requires KLiCKe)
  7. Summary report

Usage:
  pip install -r requirements.txt
  python run_analysis.py

Author: David Condrey
"""

import json
import logging
import math
import os
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

# Configure logging to stdout with bare format (reads like direct output)
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)


# ============================================================================
# STAGE 1: Environment Check
# ============================================================================
def _try_download_klicke_opendatasets(script_dir):
    """Attempt to download KLiCKe data from Kaggle using opendatasets."""
    try:
        import opendatasets as od
    except ImportError:
        return False

    log.info("\n  Attempting KLiCKe download via opendatasets (Kaggle)...")
    log.info("  You will be prompted for your Kaggle username and API key.")
    log.info("  (Find your API key at https://www.kaggle.com/settings -> API -> Create New Token)")
    try:
        od.download(
            "https://www.kaggle.com/competitions/linking-writing-processes-to-writing-quality",
            data_dir=str(script_dir),
        )
        return True
    except Exception as e:
        log.warning(f"  opendatasets download failed: {e}")
        return False


def _try_download_klicke_kaggle_api(script_dir):
    """Attempt to download KLiCKe data from Kaggle using the kaggle CLI/API."""
    try:
        import kaggle  # noqa: F401
    except ImportError:
        return False

    log.info("\n  Attempting KLiCKe download via kaggle API...")
    import subprocess
    try:
        subprocess.check_call([
            sys.executable, "-m", "kaggle", "competitions", "download",
            "-c", "linking-writing-processes-to-writing-quality",
            "-p", str(script_dir),
        ])
        # Unzip if a zip file was downloaded
        zip_path = script_dir / "linking-writing-processes-to-writing-quality.zip"
        if zip_path.exists():
            import zipfile
            dest = script_dir / "linking-writing-processes-to-writing-quality"
            dest.mkdir(exist_ok=True)
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(dest)
            zip_path.unlink()
        return True
    except Exception as e:
        log.warning(f"  kaggle API download failed: {e}")
        return False


def _detect_klicke_format(script_dir):
    """Detect which KLiCKe data format is available.

    Returns a tuple (format, has_klicke) where format is one of:
      - "local"  : original per-writer CSVs at klicke/Files/.../csv/
      - "kaggle" : Kaggle single-file format (train_logs.csv)
      - None     : no data found
    """
    # Check original local format
    local_csv_dir = (script_dir / "klicke" / "Files" / "WritingTask"
                     / "WritingTask" / "keystrokelogs" / "csv")
    if local_csv_dir.is_dir() and any(local_csv_dir.glob("*.csv")):
        return "local", True

    # Check Kaggle download directory (opendatasets puts data in a folder
    # named after the competition slug)
    kaggle_dir = script_dir / "linking-writing-processes-to-writing-quality"
    if kaggle_dir.is_dir():
        train_logs = kaggle_dir / "train_logs.csv"
        if train_logs.exists():
            return "kaggle", True

    # Also check if train_logs.csv is directly in script_dir
    if (script_dir / "train_logs.csv").exists():
        return "kaggle", True

    return None, False


def stage_environment_check():
    """Verify Python version, required packages, and data availability."""
    log.info("=" * 72)
    log.info("STAGE 1: Environment Check")
    log.info("=" * 72)

    # Python version
    v = sys.version_info
    log.info(f"\n  Python version: {v.major}.{v.minor}.{v.micro}")
    if v < (3, 8):
        log.error("  ERROR: Python >= 3.8 required.")
        sys.exit(1)
    log.info("  Python version check: PASSED")

    # Required packages
    required = {
        "numpy": "numpy",
        "scipy": "scipy",
        "pandas": "pandas",
        "matplotlib": "matplotlib",
        "sklearn": "scikit-learn",
        "datasets": "datasets",
    }
    missing = []
    for module, pip_name in required.items():
        try:
            mod = __import__(module)
            version = getattr(mod, "__version__", "unknown")
            log.info(f"  {pip_name:20s} {version}")
        except ImportError:
            log.info(f"  {pip_name:20s} MISSING")
            missing.append(pip_name)

    if missing:
        log.error(f"\n  ERROR: Missing packages: {', '.join(missing)}")
        log.error(f"  Install with: pip install {' '.join(missing)}")
        sys.exit(1)
    log.info("  Package check: PASSED")

    # Optional packages
    for module, pip_name in [("opendatasets", "opendatasets")]:
        try:
            mod = __import__(module)
            version = getattr(mod, "__version__", "unknown")
            log.info(f"  {pip_name:20s} {version} (optional)")
        except ImportError:
            log.info(f"  {pip_name:20s} not installed (optional, for Kaggle auto-download)")

    # KLiCKe data
    script_dir = Path(__file__).resolve().parent
    klicke_format, has_klicke = _detect_klicke_format(script_dir)

    if not has_klicke:
        log.info("\n  KLiCKe data: NOT FOUND locally. Attempting auto-download...")

        # Try opendatasets first (interactive Kaggle auth, no API key file needed)
        if _try_download_klicke_opendatasets(script_dir):
            klicke_format, has_klicke = _detect_klicke_format(script_dir)

        # Fall back to kaggle API
        if not has_klicke and _try_download_klicke_kaggle_api(script_dir):
            klicke_format, has_klicke = _detect_klicke_format(script_dir)

    if has_klicke:
        if klicke_format == "local":
            local_csv_dir = (script_dir / "klicke" / "Files" / "WritingTask"
                             / "WritingTask" / "keystrokelogs" / "csv")
            n_csv = len(list(local_csv_dir.glob("*.csv")))
            log.info(f"\n  KLiCKe data: FOUND ({n_csv} CSV files, local format)")
            klicke_scores = (script_dir / "klicke" / "Files" / "WritingTask"
                             / "WritingTask" / "holistic_scores.csv")
            log.info(f"  Holistic scores: {'FOUND' if klicke_scores.exists() else 'MISSING'}")
        elif klicke_format == "kaggle":
            kaggle_dir = script_dir / "linking-writing-processes-to-writing-quality"
            train_logs = kaggle_dir / "train_logs.csv"
            if not train_logs.exists():
                train_logs = script_dir / "train_logs.csv"
            import pandas as pd
            # Quick row count estimate
            n_lines = sum(1 for _ in open(train_logs)) - 1
            log.info(f"\n  KLiCKe data: FOUND (Kaggle format, ~{n_lines:,} events in train_logs.csv)")
            train_scores = kaggle_dir / "train_scores.csv"
            if not train_scores.exists():
                train_scores = script_dir / "train_scores.csv"
            log.info(f"  Holistic scores: {'FOUND' if train_scores.exists() else 'MISSING'}")
    else:
        log.info("\n  KLiCKe data: NOT FOUND (auto-download was not successful)")
        log.info("  To include KLiCKe analysis, either:")
        log.info("    1. Install opendatasets (pip install opendatasets) and re-run")
        log.info("       (you will be prompted for Kaggle credentials)")
        log.info("    2. Download manually from:")
        log.info("       https://www.kaggle.com/competitions/linking-writing-processes-to-writing-quality/data")
        log.info(f"       Place train_logs.csv and train_scores.csv in:")
        log.info(f"       {script_dir / 'linking-writing-processes-to-writing-quality' / ''}")
        log.info("    3. Or place the original KLiCKe corpus at:")
        local_csv_dir = (script_dir / "klicke" / "Files" / "WritingTask"
                         / "WritingTask" / "keystrokelogs" / "csv")
        log.info(f"       {local_csv_dir}")
        log.info("       Download from: https://keystroke.cs.cmu.edu/ (KLiCKe corpus)")
        log.info("  Continuing with ScholaWrite-only mode.")

    return has_klicke, klicke_format


# ============================================================================
# STAGE 2: ScholaWrite Analysis
# ============================================================================
def stage_scholawrite():
    """Analyze ScholaWrite dataset from HuggingFace."""
    import numpy as np
    import pandas as pd
    from scipy import stats
    from scipy.stats import wilcoxon
    from datasets import load_dataset

    log.info("\n" + "=" * 72)
    log.info("STAGE 2: ScholaWrite Analysis")
    log.info("=" * 72)

    results = {}

    # --- 2a. Load dataset ---
    log.info("\n  [2a] Loading ScholaWrite dataset from HuggingFace...")
    ds = load_dataset("minnesotanlp/scholawrite")
    df_train = pd.DataFrame(ds["train"])
    df_test = pd.DataFrame(ds["test"])
    df_all = pd.concat([df_train, df_test], ignore_index=True)

    log.info(f"  Total events: {len(df_all):,}")
    log.info(f"  Projects: {df_all['project'].nunique()}")
    log.info(f"  Authors:  {df_all['author'].nunique()}")
    log.info(f"  Labels:   {df_all['label'].nunique()}")
    log.info(f"  Columns:  {list(df_all.columns)}")

    results["total_events"] = len(df_all)
    results["n_projects"] = int(df_all["project"].nunique())
    results["n_authors"] = int(df_all["author"].nunique())

    # --- 2b. Compute IKI ---
    log.info("\n  [2b] Computing Inter-Keystroke Intervals (IKI)...")
    df_all = df_all.sort_values(["project", "author", "timestamp"]).reset_index(drop=True)
    df_all["iki_ms"] = df_all.groupby(["project", "author"])["timestamp"].diff()

    valid_iki = df_all["iki_ms"].dropna()
    valid_iki = valid_iki[(valid_iki > 10) & (valid_iki < 60000)]

    log.info(f"  Valid IKIs:  {len(valid_iki):,}")
    log.info(f"  Mean:   {valid_iki.mean():.1f} ms")
    log.info(f"  Median: {valid_iki.median():.1f} ms")
    log.info(f"  Std:    {valid_iki.std():.1f} ms")
    log.info(f"  Range:  [{valid_iki.min():.0f}, {valid_iki.max():.0f}] ms")

    results["valid_ikis"] = len(valid_iki)
    results["iki_mean_ms"] = float(valid_iki.mean())
    results["iki_median_ms"] = float(valid_iki.median())
    results["iki_std_ms"] = float(valid_iki.std())

    # --- 2c. Shannon entropy ---
    log.info("\n  [2c] Computing Shannon entropy of quantized IKI distributions...")
    QUANTIZATION_MS = 5
    WINDOW_SIZE_MS = 30000

    def compute_entropy_bits(iki_values, q=QUANTIZATION_MS):
        """Shannon entropy of IKI distribution quantized to q-ms bins, in bits."""
        quantized = (iki_values // q) * q
        probs = quantized.value_counts(normalize=True).values
        return -np.sum(probs * np.log2(probs + 1e-15))

    # Per-window entropy (30-second windows)
    window_entropies = []
    for (proj, author), group in df_all.groupby(["project", "author"]):
        group = group.sort_values("timestamp")
        timestamps = group["timestamp"].values
        ikis = group["iki_ms"].values
        if len(timestamps) < 10:
            continue
        t_start = timestamps[0]
        while t_start < timestamps[-1]:
            t_end = t_start + WINDOW_SIZE_MS
            mask = (timestamps >= t_start) & (timestamps < t_end)
            window_ikis = ikis[mask]
            window_ikis = window_ikis[~np.isnan(window_ikis)]
            window_ikis = window_ikis[(window_ikis > 10) & (window_ikis < 60000)]
            if len(window_ikis) >= 10:
                ent = compute_entropy_bits(pd.Series(window_ikis))
                window_entropies.append({
                    "project": proj, "author": author,
                    "entropy_bits": ent, "n_keystrokes": len(window_ikis),
                    "mean_iki": np.mean(window_ikis),
                })
            t_start = t_end

    df_entropy = pd.DataFrame(window_entropies)
    overall_entropy = compute_entropy_bits(valid_iki)

    log.info(f"  30s windows analyzed: {len(df_entropy):,}")
    log.info(f"  Per-window entropy:   mean={df_entropy['entropy_bits'].mean():.2f}, "
             f"median={df_entropy['entropy_bits'].median():.2f}, "
             f"std={df_entropy['entropy_bits'].std():.2f} bits")
    log.info(f"  Population per-IKI entropy: {overall_entropy:.2f} bits")
    log.info(f"  Accumulated per checkpoint (50 keys): {50 * overall_entropy:.1f} bits")
    log.info(f"  Windows above 3.0-bit threshold: "
             f"{(df_entropy['entropy_bits'] > 3.0).sum()}/{len(df_entropy)} "
             f"({100*(df_entropy['entropy_bits'] > 3.0).mean():.1f}%)")

    results["entropy_per_iki_bits"] = float(overall_entropy)
    results["entropy_per_checkpoint_bits"] = float(50 * overall_entropy)
    results["entropy_window_mean"] = float(df_entropy["entropy_bits"].mean())

    # --- 2d. Cognitive Load Correlation (CLC) ---
    log.info("\n  [2d] Computing Cognitive Load Correlation (CLC)...")

    # ScholaWrite has 15 fine-grained labels mapped to 3 cognitive load levels
    COGNITIVE_LOAD = {
        # High (3): planning, structuring, argumentation
        "Idea Generation": 3, "Structural": 3, "Claim Making": 3,
        # Medium (2): revision-oriented quality concerns
        "Fluency": 2, "Coherence": 2, "Clarity": 2, "Audience": 2,
        "Scientific Accuracy": 2,
        # Low (1): mechanical text production
        "Text Production": 1, "Object Insertion": 1, "Citation Integration": 1,
        "Formatting": 1, "Cross-referencing": 1, "Syntax": 1, "Jargon Usage": 1,
    }

    df_all["cog_load"] = df_all["label"].map(COGNITIVE_LOAD).fillna(1)

    # Windowed CLC: Spearman rho between cognitive load and IKI per 30s window
    clc_values = []
    for (proj, author), group in df_all.groupby(["project", "author"]):
        group = group.sort_values("timestamp")
        timestamps = group["timestamp"].values
        ikis = group["iki_ms"].values
        cog_loads = group["cog_load"].values
        if len(timestamps) < 20:
            continue
        t_start = timestamps[0]
        while t_start < timestamps[-1]:
            t_end = t_start + WINDOW_SIZE_MS
            mask = (timestamps >= t_start) & (timestamps < t_end)
            w_ikis = ikis[mask]
            w_cog = cog_loads[mask]
            valid = ~np.isnan(w_ikis) & (w_ikis > 10) & (w_ikis < 60000)
            w_ikis = w_ikis[valid]
            w_cog = w_cog[valid]
            if len(w_ikis) >= 10 and np.std(w_cog) > 0:
                try:
                    rho, pval = stats.spearmanr(w_cog, w_ikis)
                    if not np.isnan(rho):
                        clc_values.append({
                            "project": proj, "author": author,
                            "rho": rho, "pval": pval, "n": len(w_ikis),
                        })
                except Exception:
                    pass
            t_start = t_end

    df_clc = pd.DataFrame(clc_values)
    log.info(f"  Windows with CLC computed: {len(df_clc):,}")
    log.info(f"  Mean CLC (Spearman rho): {df_clc['rho'].mean():.4f}")
    log.info(f"  Median CLC:              {df_clc['rho'].median():.4f}")
    log.info(f"  Std CLC:                 {df_clc['rho'].std():.4f}")
    log.info(f"  Windows with rho > 0.15: {(df_clc['rho'] > 0.15).sum()}/{len(df_clc)} "
             f"({100*(df_clc['rho'] > 0.15).mean():.1f}%)")
    log.info(f"  Windows with rho > 0.0:  {(df_clc['rho'] > 0.0).sum()}/{len(df_clc)} "
             f"({100*(df_clc['rho'] > 0.0).mean():.1f}%)")
    log.info(f"  Significant (p<0.05):    {(df_clc['pval'] < 0.05).sum()}/{len(df_clc)} "
             f"({100*(df_clc['pval'] < 0.05).mean():.1f}%)")

    # Overall CLC across all valid data
    all_valid = df_all.dropna(subset=["iki_ms"]).copy()
    all_valid = all_valid[(all_valid["iki_ms"] > 10) & (all_valid["iki_ms"] < 60000)]
    overall_rho, overall_pval = stats.spearmanr(all_valid["cog_load"], all_valid["iki_ms"])
    log.info(f"\n  Overall CLC (all data): rho={overall_rho:.4f}, p={overall_pval:.2e}")

    results["clc_overall_rho"] = float(overall_rho)
    results["clc_overall_pval"] = float(overall_pval)
    results["clc_window_mean_rho"] = float(df_clc["rho"].mean())
    results["clc_windows_total"] = len(df_clc)
    results["clc_windows_above_015"] = int((df_clc["rho"] > 0.15).sum())
    results["clc_pct_above_015"] = float(100 * (df_clc["rho"] > 0.15).mean())

    # Per-author CLC with Wilcoxon signed-rank test (avoids pooling violation)
    per_author_rho = []
    for author, group in all_valid.groupby("author"):
        if len(group) >= 20 and group["cog_load"].std() > 0:
            r, p = stats.spearmanr(group["cog_load"], group["iki_ms"])
            if not np.isnan(r):
                per_author_rho.append(r)

    if per_author_rho:
        w_stat, w_pval = wilcoxon(per_author_rho)
        log.info(f"  Per-author CLC (Wilcoxon): median rho={np.median(per_author_rho):.4f}, "
                 f"p={w_pval:.2e}, n={len(per_author_rho)}")
        results["clc_per_author_median_rho"] = float(np.median(per_author_rho))
        results["clc_per_author_wilcoxon_p"] = float(w_pval)

    # --- 2e. Composition vs transcription discrimination ---
    log.info("\n  [2e] Composition vs. Transcription Discrimination...")
    # In ScholaWrite, all data is genuine composition. We compare high-CLC
    # windows (composition signature) vs low-CLC windows (transcription-like).
    high_load = df_clc[df_clc["rho"] > 0.15]
    low_load = df_clc[df_clc["rho"] <= 0.0]

    log.info(f"  Composition-like windows (rho>0.15):  {len(high_load):,}")
    log.info(f"  Transcription-like windows (rho<=0):  {len(low_load):,}")

    if len(high_load) > 0 and len(low_load) > 0:
        mean_comp = high_load["rho"].mean()
        mean_trans = low_load["rho"].mean()
        pooled_std = np.sqrt((high_load["rho"].std()**2 + low_load["rho"].std()**2) / 2)
        cohens_d = (mean_comp - mean_trans) / pooled_std if pooled_std > 0 else 0
        u_stat, u_pval = stats.mannwhitneyu(
            high_load["rho"], low_load["rho"], alternative="greater"
        )
        log.info(f"  Mean rho (composition):   {mean_comp:.4f}")
        log.info(f"  Mean rho (transcription): {mean_trans:.4f}")
        log.info(f"  Cohen's d:    {cohens_d:.3f}")
        log.info(f"  Mann-Whitney U={u_stat:.1f}, p={u_pval:.2e}")

        results["disc_cohens_d"] = float(cohens_d)
        results["disc_mann_whitney_p"] = float(u_pval)

    # --- 2f. IKI by cognitive operation type ---
    log.info("\n  [2f] IKI Distribution by Cognitive Operation Type...")
    # ScholaWrite's "high-level" column: PLANNING, IMPLEMENTATION, REVISION
    for hl in ["PLANNING", "IMPLEMENTATION", "REVISION"]:
        subset = all_valid[all_valid["high-level"] == hl]["iki_ms"]
        if len(subset) > 0:
            log.info(f"  {hl:15s}: n={len(subset):>6,}, mean={subset.mean():>8.1f}ms, "
                     f"median={subset.median():>7.1f}ms, std={subset.std():>8.1f}ms")

    demanding = all_valid[all_valid["high-level"].isin(["PLANNING", "REVISION"])]["iki_ms"]
    simple = all_valid[all_valid["high-level"] == "IMPLEMENTATION"]["iki_ms"]

    if len(demanding) > 0 and len(simple) > 0:
        ratio = demanding.mean() / simple.mean()
        d_stat, d_pval = stats.mannwhitneyu(demanding, simple, alternative="greater")
        d_pooled = np.sqrt((demanding.std()**2 + simple.std()**2) / 2)
        cohens_d_hl = (demanding.mean() - simple.mean()) / d_pooled if d_pooled > 0 else 0

        log.info(f"\n  Demanding/Simple IKI ratio: {ratio:.2f}x")
        log.info(f"  Mann-Whitney p: {d_pval:.2e}")
        log.info(f"  Cohen's d:      {cohens_d_hl:.3f}")

        results["iki_ratio_demanding_simple"] = float(ratio)
        results["iki_cohens_d_highlevel"] = float(cohens_d_hl)

    return results


# ============================================================================
# STAGE 3: KLiCKe Analysis
# ============================================================================
def _load_klicke_data(klicke_format):
    """Load KLiCKe data from either local or Kaggle format.

    Returns (df_all, scores_file_path) where df_all has normalized columns:
      writer_id, DownTime, UpTime, ActionTime, Activity, DownEvent, UpEvent,
      Cursorposition, WordCount, TextChange
    """
    import pandas as pd

    script_dir = Path(__file__).resolve().parent

    if klicke_format == "local":
        CSV_DIR = (script_dir / "klicke" / "Files" / "WritingTask"
                   / "WritingTask" / "keystrokelogs" / "csv")
        SCORES_FILE = (script_dir / "klicke" / "Files" / "WritingTask"
                       / "WritingTask" / "holistic_scores.csv")

        log.info("  Loading KLiCKe from local per-writer CSVs...")
        all_rows = []
        csv_files = sorted(CSV_DIR.glob("*.csv"))
        n_files = len(csv_files)
        log.info(f"  Found {n_files} writer files")

        for i, f in enumerate(csv_files):
            if (i + 1) % 1000 == 0:
                log.info(f"    Loading file {i+1}/{n_files}...")
            try:
                df = pd.read_csv(f)
                df["writer_id"] = f.stem
                all_rows.append(df)
            except Exception:
                pass

        df_all = pd.concat(all_rows, ignore_index=True)
        return df_all, SCORES_FILE

    elif klicke_format == "kaggle":
        kaggle_dir = script_dir / "linking-writing-processes-to-writing-quality"
        train_logs = kaggle_dir / "train_logs.csv"
        if not train_logs.exists():
            train_logs = script_dir / "train_logs.csv"

        SCORES_FILE = kaggle_dir / "train_scores.csv"
        if not SCORES_FILE.exists():
            SCORES_FILE = script_dir / "train_scores.csv"

        log.info("  Loading KLiCKe from Kaggle train_logs.csv...")
        df_raw = pd.read_csv(train_logs)
        log.info(f"  Raw events loaded: {len(df_raw):,}")

        # Normalize Kaggle columns to match local format:
        #   Kaggle: id, event_id, down_time, up_time, action_time, activity,
        #           down_event, up_event, text_change, cursor_position, word_count
        #   Local:  DownEventID, UpEventID, DownTime, UpTime, ActionTime,
        #           DownEvent, UpEvent, Cursorposition, WordCount, TextChange, Activity
        col_map = {
            "id": "writer_id",
            "down_time": "DownTime",
            "up_time": "UpTime",
            "action_time": "ActionTime",
            "activity": "Activity",
            "down_event": "DownEvent",
            "up_event": "UpEvent",
            "cursor_position": "Cursorposition",
            "word_count": "WordCount",
            "text_change": "TextChange",
            "event_id": "DownEventID",
        }
        df_all = df_raw.rename(columns=col_map)
        # Ensure writer_id is string for consistency with local format
        df_all["writer_id"] = df_all["writer_id"].astype(str)
        return df_all, SCORES_FILE

    else:
        raise ValueError(f"Unknown KLiCKe format: {klicke_format}")


def stage_klicke(klicke_format):
    """Analyze KLiCKe corpus keystroke logs."""
    import numpy as np
    import pandas as pd
    from scipy import stats

    log.info("\n" + "=" * 72)
    log.info("STAGE 3: KLiCKe Corpus Analysis")
    log.info("=" * 72)

    script_dir = Path(__file__).resolve().parent
    QUANTIZATION_MS = 5
    WINDOW_SIZE_MS = 30000

    results = {}

    def compute_entropy_bits(iki_values, q=QUANTIZATION_MS):
        quantized = (iki_values // q) * q
        probs = quantized.value_counts(normalize=True).values
        return -np.sum(probs * np.log2(probs + 1e-15))

    # --- 3a. Load keystroke logs ---
    log.info("\n  [3a] Loading KLiCKe keystroke logs...")
    df_all, SCORES_FILE = _load_klicke_data(klicke_format)
    log.info(f"  Total events: {len(df_all):,}")
    log.info(f"  Writers:      {df_all['writer_id'].nunique():,}")
    log.info(f"  Columns:      {list(df_all.columns)}")

    results["n_writers"] = int(df_all["writer_id"].nunique())
    results["total_events"] = len(df_all)

    # Activity distribution
    log.info("  Activity distribution:")
    for act, count in df_all["Activity"].value_counts().items():
        log.info(f"    {act}: {count:,} ({100*count/len(df_all):.1f}%)")

    # --- 3b. Compute IKI ---
    log.info(f"\n  [3b] Computing IKI...")
    df_all = df_all.sort_values(["writer_id", "DownTime"]).reset_index(drop=True)
    df_all["iki_ms"] = df_all.groupby("writer_id")["DownTime"].diff()

    valid_iki = df_all["iki_ms"].dropna()
    valid_iki = valid_iki[(valid_iki > 10) & (valid_iki < 60000)]

    log.info(f"  Valid IKIs:  {len(valid_iki):,}")
    log.info(f"  Mean:   {valid_iki.mean():.1f} ms")
    log.info(f"  Median: {valid_iki.median():.1f} ms")
    log.info(f"  Std:    {valid_iki.std():.1f} ms")

    results["valid_ikis"] = len(valid_iki)
    results["iki_mean_ms"] = float(valid_iki.mean())
    results["iki_median_ms"] = float(valid_iki.median())

    # Per-writer IKI stats
    writer_valid = df_all.dropna(subset=["iki_ms"]).copy()
    writer_valid = writer_valid[(writer_valid["iki_ms"] > 10) & (writer_valid["iki_ms"] < 60000)]
    per_writer = writer_valid.groupby("writer_id")["iki_ms"].agg(["mean", "median", "std", "count"])
    log.info(f"  Per-writer IKI means: pop_mean={per_writer['mean'].mean():.1f}, "
             f"pop_median={per_writer['mean'].median():.1f}")

    # --- 3c. Entropy ---
    log.info(f"\n  [3c] Computing entropy...")
    overall_entropy = compute_entropy_bits(valid_iki)
    log.info(f"  Population per-IKI entropy: {overall_entropy:.2f} bits")
    log.info(f"  Accumulated per checkpoint (50 keys): {50 * overall_entropy:.1f} bits")
    log.info(f"  Paper claim >=205 bits: {'VALIDATED' if 50 * overall_entropy >= 205 else 'NOT MET'}")

    results["entropy_per_iki_bits"] = float(overall_entropy)
    results["entropy_per_checkpoint_bits"] = float(50 * overall_entropy)

    # Per-writer entropy
    writer_entropies = []
    for wid, group in writer_valid.groupby("writer_id"):
        if len(group) >= 30:
            ent = compute_entropy_bits(group["iki_ms"])
            writer_entropies.append({"writer_id": wid, "entropy_bits": ent, "n": len(group)})

    df_went = pd.DataFrame(writer_entropies)
    log.info(f"\n  Per-writer entropy ({len(df_went)} writers with >=30 keystrokes):")
    log.info(f"    Mean:   {df_went['entropy_bits'].mean():.2f} bits")
    log.info(f"    Median: {df_went['entropy_bits'].median():.2f} bits")
    log.info(f"    Std:    {df_went['entropy_bits'].std():.2f} bits")
    log.info(f"    Above 3.0 bits: {(df_went['entropy_bits'] > 3.0).sum()}/{len(df_went)} "
             f"({100*(df_went['entropy_bits'] > 3.0).mean():.1f}%)")

    # 30s window entropy
    window_entropies = []
    for wid, group in writer_valid.groupby("writer_id"):
        group = group.sort_values("DownTime")
        timestamps = group["DownTime"].values
        ikis = group["iki_ms"].values
        if len(timestamps) < 10:
            continue
        t_start = timestamps[0]
        while t_start < timestamps[-1]:
            t_end = t_start + WINDOW_SIZE_MS
            mask = (timestamps >= t_start) & (timestamps < t_end)
            w_ikis = ikis[mask]
            w_ikis = w_ikis[~np.isnan(w_ikis)]
            w_ikis = w_ikis[(w_ikis > 10) & (w_ikis < 60000)]
            if len(w_ikis) >= 10:
                window_entropies.append({
                    "writer_id": wid,
                    "entropy_bits": compute_entropy_bits(pd.Series(w_ikis)),
                    "n_keystrokes": len(w_ikis),
                })
            t_start = t_end

    df_winent = pd.DataFrame(window_entropies)
    log.info(f"\n  30s window entropy ({len(df_winent):,} windows):")
    log.info(f"    Mean: {df_winent['entropy_bits'].mean():.2f} bits")
    log.info(f"    Above 3.0 bits: {(df_winent['entropy_bits'] > 3.0).sum()}/{len(df_winent)} "
             f"({100*(df_winent['entropy_bits'] > 3.0).mean():.1f}%)")

    # --- 3d. CLC ---
    log.info(f"\n  [3d] Computing CLC...")
    COGNITIVE_LOAD = {"Nonproduction": 3, "Remove/Cut": 2, "Input": 1}
    df_all["cog_load"] = df_all["Activity"].map(COGNITIVE_LOAD).fillna(1)

    all_valid = df_all.dropna(subset=["iki_ms"]).copy()
    all_valid = all_valid[(all_valid["iki_ms"] > 10) & (all_valid["iki_ms"] < 60000)]

    overall_rho, overall_pval = stats.spearmanr(all_valid["cog_load"], all_valid["iki_ms"])
    log.info(f"  Overall CLC: rho={overall_rho:.4f}, p={overall_pval:.2e}")

    results["clc_overall_rho"] = float(overall_rho)

    # Per-writer CLC
    writer_clcs = []
    for wid, group in all_valid.groupby("writer_id"):
        if len(group) >= 30 and group["cog_load"].std() > 0:
            try:
                rho, pval = stats.spearmanr(group["cog_load"], group["iki_ms"])
                if not np.isnan(rho):
                    writer_clcs.append({"writer_id": wid, "rho": rho, "pval": pval, "n": len(group)})
            except Exception:
                pass

    df_wclc = pd.DataFrame(writer_clcs)
    log.info(f"\n  Per-writer CLC ({len(df_wclc)} writers):")
    log.info(f"    Mean rho:  {df_wclc['rho'].mean():.4f}")
    log.info(f"    Median rho: {df_wclc['rho'].median():.4f}")
    log.info(f"    Positive CLC: {(df_wclc['rho'] > 0.0).sum()}/{len(df_wclc)} "
             f"({100*(df_wclc['rho'] > 0.0).mean():.1f}%)")
    log.info(f"    Significant (p<0.05): {(df_wclc['pval'] < 0.05).sum()}/{len(df_wclc)} "
             f"({100*(df_wclc['pval'] < 0.05).mean():.1f}%)")

    results["clc_per_writer_mean_rho"] = float(df_wclc["rho"].mean())
    results["clc_per_writer_median_rho"] = float(df_wclc["rho"].median())
    results["clc_pct_positive"] = float(100 * (df_wclc["rho"] > 0.0).mean())
    results["clc_pct_significant"] = float(100 * (df_wclc["pval"] < 0.05).mean())

    # CLC proxy for retype simulation: per-writer correlation between
    # IKI variance and IKI mean across 30s windows
    writer_clc_proxy = {}
    for wid, group in all_valid.groupby("writer_id"):
        group = group.sort_values("DownTime")
        timestamps = group["DownTime"].values
        ikis = group["iki_ms"].values
        if len(timestamps) < 30:
            continue
        window_means, window_vars = [], []
        t_start = timestamps[0]
        while t_start < timestamps[-1]:
            t_end = t_start + WINDOW_SIZE_MS
            mask = (timestamps >= t_start) & (timestamps < t_end)
            w_ikis = ikis[mask]
            w_ikis = w_ikis[~np.isnan(w_ikis)]
            w_ikis = w_ikis[(w_ikis > 10) & (w_ikis < 60000)]
            if len(w_ikis) >= 5:
                window_means.append(np.mean(w_ikis))
                window_vars.append(np.var(w_ikis))
            t_start = t_end
        if len(window_means) >= 3:
            try:
                rho, _ = stats.spearmanr(window_means, window_vars)
                if not np.isnan(rho):
                    writer_clc_proxy[wid] = rho
            except Exception:
                pass

    # --- 3e. IKI by activity ---
    log.info(f"\n  [3e] IKI by activity type:")
    for act in ["Input", "Remove/Cut", "Nonproduction"]:
        subset = all_valid[all_valid["Activity"] == act]["iki_ms"]
        if len(subset) > 0:
            log.info(f"    {act:20s}: n={len(subset):>9,}, mean={subset.mean():>8.1f}ms, "
                     f"median={subset.median():>7.1f}ms, std={subset.std():>8.1f}ms")

    demanding = all_valid[all_valid["Activity"].isin(["Nonproduction", "Remove/Cut"])]["iki_ms"]
    simple = all_valid[all_valid["Activity"] == "Input"]["iki_ms"]
    if len(demanding) > 0 and len(simple) > 0:
        ratio = demanding.mean() / simple.mean()
        d_pooled = np.sqrt((demanding.std()**2 + simple.std()**2) / 2)
        cohens_d = (demanding.mean() - simple.mean()) / d_pooled if d_pooled > 0 else 0
        log.info(f"\n    Demanding/Simple ratio: {ratio:.2f}x, Cohen's d: {cohens_d:.3f}")
        results["iki_ratio_demanding_simple"] = float(ratio)
        results["iki_cohens_d_activity"] = float(cohens_d)

    # --- 3f. Quality score correlation ---
    if SCORES_FILE.exists():
        log.info(f"\n  [3f] Quality score correlation...")
        scores = pd.read_csv(SCORES_FILE, encoding="latin-1")
        # Normalize column names: local format has ID/Score, Kaggle has id/score
        scores.columns = [c.strip() for c in scores.columns]
        if "id" in scores.columns and "ID" not in scores.columns:
            scores.rename(columns={"id": "ID", "score": "Score"}, inplace=True)
        scores["writer_id"] = scores["ID"].astype(str)

        per_writer_metrics = writer_valid.groupby("writer_id").agg(
            mean_iki=("iki_ms", "mean"),
            std_iki=("iki_ms", "std"),
        ).reset_index()

        if len(df_wclc) > 0:
            per_writer_metrics = per_writer_metrics.merge(
                df_wclc[["writer_id", "rho"]].rename(columns={"rho": "clc_rho"}),
                on="writer_id", how="left"
            )
        if len(df_went) > 0:
            per_writer_metrics = per_writer_metrics.merge(
                df_went[["writer_id", "entropy_bits"]],
                on="writer_id", how="left"
            )

        merged = per_writer_metrics.merge(scores[["writer_id", "Score"]], on="writer_id", how="inner")
        log.info(f"    Writers with scores: {len(merged):,}")

        if len(merged) > 10:
            for col in ["mean_iki", "std_iki", "clc_rho", "entropy_bits"]:
                if col in merged.columns:
                    valid_m = merged.dropna(subset=[col, "Score"])
                    if len(valid_m) > 10:
                        rho, pval = stats.spearmanr(valid_m[col], valid_m["Score"])
                        log.info(f"    {col:15s} vs Score: rho={rho:.4f}, p={pval:.2e} (n={len(valid_m)})")

    # Return the full dataframe and writer data for downstream stages
    return results, df_all, writer_valid, df_wclc, writer_clc_proxy


# ============================================================================
# STAGE 4: Adversarial Retype Simulation
# ============================================================================
def stage_retype_simulation(df_all):
    """Simulate four adversarial retype strategies against genuine sessions."""
    import numpy as np
    import pandas as pd
    from scipy import stats

    log.info("\n" + "=" * 72)
    log.info("STAGE 4: Adversarial Retype Simulation")
    log.info("=" * 72)

    script_dir = Path(__file__).resolve().parent

    QUANTIZATION_MS = 5
    MIN_EVENTS = 100
    MAX_WRITERS = 500
    SESSION_LEN = 200
    COGNITIVE_LOAD = {"Nonproduction": 3, "Remove/Cut": 2, "Input": 1}

    results = {}

    # --- Helper functions ---
    def entropy_bits(ikis, q=QUANTIZATION_MS):
        quantized = (ikis // q) * q
        _, counts = np.unique(quantized, return_counts=True)
        probs = counts / counts.sum()
        return -np.sum(probs * np.log2(probs + 1e-15))

    def autocorr_lag1(ikis):
        if len(ikis) < 3:
            return 0.0
        x = ikis - ikis.mean()
        c0 = np.dot(x, x)
        if c0 == 0:
            return 0.0
        return np.dot(x[:-1], x[1:]) / c0

    def clc_proxy(ikis, activities):
        cog = np.array([COGNITIVE_LOAD.get(a, 1) for a in activities], dtype=float)
        if len(ikis) < 10 or np.std(cog) == 0:
            return 0.0
        rho, _ = stats.spearmanr(cog, ikis)
        return 0.0 if np.isnan(rho) else rho

    def markov_retype(ikis, n_out, n_bins=20):
        """First-order Markov chain retype: discretize IKIs into equal-frequency
        bins, build transition matrix, sample chain, map back to continuous."""
        bin_edges = np.percentile(ikis, np.linspace(0, 100, n_bins + 1))
        bin_edges[0] -= 1
        bin_edges[-1] += 1
        bin_indices = np.clip(np.digitize(ikis, bin_edges) - 1, 0, n_bins - 1)

        trans_counts = np.zeros((n_bins, n_bins), dtype=float)
        for i in range(len(bin_indices) - 1):
            trans_counts[bin_indices[i], bin_indices[i + 1]] += 1
        trans_counts += 0.01  # Laplace smoothing
        trans_probs = trans_counts / trans_counts.sum(axis=1, keepdims=True)

        init_probs = np.bincount(bin_indices, minlength=n_bins).astype(float)
        init_probs /= init_probs.sum()

        synthetic_bins = np.zeros(n_out, dtype=int)
        synthetic_bins[0] = np.random.choice(n_bins, p=init_probs)
        for i in range(1, n_out):
            synthetic_bins[i] = np.random.choice(n_bins, p=trans_probs[synthetic_bins[i - 1]])

        synthetic_ikis = np.zeros(n_out, dtype=float)
        for i in range(n_out):
            lo, hi = bin_edges[synthetic_bins[i]], bin_edges[synthetic_bins[i] + 1]
            synthetic_ikis[i] = np.random.uniform(lo, hi)
        return np.clip(synthetic_ikis, 10, 60000)

    def extract_features(ikis, activities=None):
        return {
            "entropy": float(entropy_bits(ikis)),
            "autocorr_lag1": float(autocorr_lag1(ikis)),
            "iki_mean": float(ikis.mean()),
            "iki_std": float(ikis.std()),
            "iki_log_var": float(np.log(ikis.var() + 1)),
            "pause_freq": float((ikis > 2000).mean()),
            "clc_proxy": float(clc_proxy(ikis, activities)) if activities is not None else 0.0,
        }

    # --- 4a. Build writer sessions from pre-loaded df_all ---
    log.info("\n  [4a] Building writer sessions from loaded data...")
    writer_data = {}

    for wid, group in df_all.groupby("writer_id"):
        group = group.sort_values("DownTime").reset_index(drop=True)
        iki = group["DownTime"].diff().values[1:]
        act = group["Activity"].values[1:]
        valid = (iki > 10) & (iki < 60000)
        iki, act = iki[valid].astype(float), act[valid]
        if len(iki) >= MIN_EVENTS:
            writer_data[str(wid)] = {"ikis": iki, "activities": act}

    log.info(f"  Eligible writers (>={MIN_EVENTS} events): {len(writer_data)}")

    all_wids = sorted(writer_data.keys())
    sampled_wids = sorted(random.sample(all_wids, min(MAX_WRITERS, len(all_wids))))
    log.info(f"  Using {len(sampled_wids)} writers for simulation")

    # --- 4b. Generate genuine + forged sessions ---
    log.info("\n  [4b] Generating genuine and forged sessions...")
    records = []

    for idx, wid in enumerate(sampled_wids):
        if (idx + 1) % 100 == 0:
            log.info(f"    {idx+1}/{len(sampled_wids)} writers...")

        w = writer_data[wid]
        ikis_full, acts_full = w["ikis"], w["activities"]

        # Genuine session: contiguous window
        if len(ikis_full) > SESSION_LEN:
            start = random.randint(0, len(ikis_full) - SESSION_LEN)
            g_ikis = ikis_full[start:start + SESSION_LEN]
            g_acts = acts_full[start:start + SESSION_LEN]
        else:
            g_ikis, g_acts = ikis_full, acts_full

        feat = extract_features(g_ikis, g_acts)
        feat.update({"writer_id": wid, "session_type": "genuine", "label": 0})
        records.append(feat)

        # Attack 1: Constant-rate (all IKIs = writer's median)
        const_ikis = np.full(SESSION_LEN, np.median(ikis_full))
        feat = extract_features(const_ikis)
        feat.update({"writer_id": wid, "session_type": "attack_constant", "label": 1})
        records.append(feat)

        # Attack 2: IID sampling (destroys autocorrelation)
        iid_ikis = np.random.choice(ikis_full, size=SESSION_LEN, replace=True)
        feat = extract_features(iid_ikis)
        feat.update({"writer_id": wid, "session_type": "attack_iid", "label": 1})
        records.append(feat)

        # Attack 3: Cross-writer sampling
        donor = random.choice([w2 for w2 in all_wids if w2 != wid])
        donor_ikis = writer_data[donor]["ikis"] if donor in writer_data else ikis_full
        cross_ikis = np.random.choice(donor_ikis, size=SESSION_LEN, replace=True)
        feat = extract_features(cross_ikis)
        feat.update({"writer_id": wid, "session_type": "attack_cross", "label": 1})
        records.append(feat)

        # Attack 4: Markov-chain retype (preserves lag-1 autocorrelation)
        markov_ikis = markov_retype(ikis_full, SESSION_LEN)
        feat = extract_features(markov_ikis)
        feat.update({"writer_id": wid, "session_type": "attack_markov", "label": 1})
        records.append(feat)

    df_sessions = pd.DataFrame(records)
    log.info(f"\n  Total sessions: {len(df_sessions)}")
    log.info(f"    Genuine: {(df_sessions['label'] == 0).sum()}")
    log.info(f"    Forged:  {(df_sessions['label'] == 1).sum()}")

    # --- 4c. Feature distributions by attack type ---
    log.info("\n  [4c] Feature distributions by session type:")
    feature_cols = ["entropy", "autocorr_lag1", "iki_mean", "iki_std", "iki_log_var", "pause_freq", "clc_proxy"]
    for stype in ["genuine", "attack_constant", "attack_iid", "attack_cross", "attack_markov"]:
        subset = df_sessions[df_sessions["session_type"] == stype]
        log.info(f"\n    {stype} (n={len(subset)}):")
        for fc in feature_cols:
            vals = subset[fc]
            log.info(f"      {fc:18s}: mean={vals.mean():>10.4f}, std={vals.std():>10.4f}")

    # Save session features
    session_csv = script_dir / "retype_sessions.csv"
    df_sessions.to_csv(session_csv, index=False)
    log.info(f"\n  Session features saved to {session_csv}")

    results["n_writers"] = len(sampled_wids)
    results["total_sessions"] = len(df_sessions)
    results["genuine_sessions"] = int((df_sessions["label"] == 0).sum())
    results["forged_sessions"] = int((df_sessions["label"] == 1).sum())

    return results, df_sessions


# ============================================================================
# STAGE 5: ROC Classification
# ============================================================================
def stage_roc_classification():
    """Leave-one-writer-out logistic regression classification."""
    import numpy as np
    import pandas as pd
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score, roc_curve
    from sklearn.preprocessing import StandardScaler

    log.info("\n" + "=" * 72)
    log.info("STAGE 5: ROC Classification (Leave-One-Writer-Out CV)")
    log.info("=" * 72)

    script_dir = Path(__file__).resolve().parent
    session_csv = script_dir / "retype_sessions.csv"
    if not session_csv.exists():
        log.error("  ERROR: retype_sessions.csv not found. Stage 4 must run first.")
        return {}

    df = pd.read_csv(session_csv)
    log.info(f"\n  Loaded {len(df)} sessions ({(df['label']==0).sum()} genuine, "
             f"{(df['label']==1).sum()} forged)")

    feature_cols = ["entropy", "autocorr_lag1", "iki_mean", "iki_std",
                    "iki_log_var", "pause_freq", "clc_proxy"]
    attack_types = ["attack_constant", "attack_iid", "attack_cross", "attack_markov"]

    results = {}

    for attack in attack_types + ["all_attacks"]:
        log.info(f"\n  Evaluating: {attack}")

        if attack == "all_attacks":
            df_eval = df.copy()
        else:
            df_eval = pd.concat([df[df["session_type"] == "genuine"],
                                 df[df["session_type"] == attack]])

        writers = df_eval["writer_id"].unique()
        y_true_all, y_score_all, y_pred_all = [], [], []
        fold_coefs = []

        # Leave-one-writer-out cross-validation
        for w in writers:
            test = df_eval[df_eval["writer_id"] == w]
            train = df_eval[df_eval["writer_id"] != w]
            if (len(test) == 0 or len(train[train["label"] == 0]) == 0
                    or len(train[train["label"] == 1]) == 0):
                continue

            X_train = train[feature_cols].values
            y_train = train["label"].values
            X_test = test[feature_cols].values
            y_test = test["label"].values

            scaler = StandardScaler()
            X_train_s = scaler.fit_transform(X_train)
            X_test_s = scaler.transform(X_test)

            clf = LogisticRegression(max_iter=1000, random_state=42)
            clf.fit(X_train_s, y_train)

            y_score = clf.predict_proba(X_test_s)[:, 1]
            y_pred = clf.predict(X_test_s)

            y_true_all.extend(y_test.tolist())
            y_score_all.extend(y_score.tolist())
            y_pred_all.extend(y_pred.tolist())
            fold_coefs.append(clf.coef_[0].copy())

        y_true_all = np.array(y_true_all)
        y_score_all = np.array(y_score_all)
        y_pred_all = np.array(y_pred_all)

        auc = roc_auc_score(y_true_all, y_score_all)
        fpr, tpr, thresholds = roc_curve(y_true_all, y_score_all)
        fnr = 1 - tpr
        eer_idx = np.argmin(np.abs(fpr - fnr))
        eer = (fpr[eer_idx] + fnr[eer_idx]) / 2

        # Operating points
        operating_points = {}
        for target_frr in [0.01, 0.05, 0.10]:
            idx = np.argmin(np.abs(fnr - target_frr))
            operating_points[f"FAR_at_{int(target_frr*100)}pct_FRR"] = round(float(fpr[idx]), 4)

        # Confusion matrix at default threshold
        tp = int(((y_true_all == 1) & (y_pred_all == 1)).sum())
        fp = int(((y_true_all == 0) & (y_pred_all == 1)).sum())
        tn = int(((y_true_all == 0) & (y_pred_all == 0)).sum())
        fn = int(((y_true_all == 1) & (y_pred_all == 0)).sum())
        accuracy = (tp + tn) / len(y_true_all) if len(y_true_all) > 0 else 0

        result = {
            "auc": round(auc, 4),
            "eer": round(eer, 4),
            "accuracy": round(accuracy, 4),
            "operating_points": operating_points,
            "confusion_matrix": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        }
        results[attack] = result

        log.info(f"    AUC:      {auc:.4f}")
        log.info(f"    EER:      {eer:.4f}")
        log.info(f"    Accuracy: {accuracy:.4f}")
        log.info(f"    FAR@5%FRR: {operating_points.get('FAR_at_5pct_FRR', 'N/A')}")

        # Feature importance for all_attacks
        if attack == "all_attacks" and fold_coefs:
            mean_coefs = np.mean(fold_coefs, axis=0)
            std_coefs = np.std(fold_coefs, axis=0)
            log.info("\n  Feature importance (averaged |coef| across CV folds):")
            importance = {}
            for feat, coef, std in zip(feature_cols, mean_coefs, std_coefs):
                log.info(f"    {feat:18s}: |coef|={abs(coef):.4f} (std={std:.4f})")
                importance[feat] = round(float(abs(coef)), 4)
            results["feature_importance"] = importance

    return results


# ============================================================================
# STAGE 6: Effect Sizes and Figures
# ============================================================================
def stage_effect_sizes_and_figures(df_klicke):
    """Compute effect sizes and generate publication-quality figures."""
    import numpy as np
    import pandas as pd
    from scipy import stats
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    log.info("\n" + "=" * 72)
    log.info("STAGE 6: Effect Sizes and Figures")
    log.info("=" * 72)

    script_dir = Path(__file__).resolve().parent
    fig_dir = script_dir / "figures"
    fig_dir.mkdir(exist_ok=True)
    QUANTIZATION_MS = 5
    MIN_EVENTS = 50
    COGNITIVE_LOAD = {"Nonproduction": 3, "Remove/Cut": 2, "Input": 1}

    # Publication-quality style
    plt.rcParams.update({
        "font.family": "serif", "font.size": 10,
        "axes.titlesize": 12, "axes.labelsize": 11,
        "xtick.labelsize": 9, "ytick.labelsize": 9,
        "legend.fontsize": 9, "figure.dpi": 300,
        "savefig.dpi": 300, "savefig.bbox": "tight",
        "axes.spines.top": False, "axes.spines.right": False,
    })

    results = {}

    # --- 6a. Compute per-writer features from pre-loaded data ---
    log.info("\n  [6a] Computing per-writer features...")
    records = []
    window_records = []
    writer_ids = sorted(df_klicke["writer_id"].unique())
    n_writers = len(writer_ids)

    for i, wid in enumerate(writer_ids):
        if (i + 1) % 1000 == 0:
            log.info(f"    {i+1}/{n_writers} writers processed...")

        df = df_klicke[df_klicke["writer_id"] == wid].sort_values("DownTime").reset_index(drop=True)
        iki = df["DownTime"].diff().dropna()
        iki = iki[(iki > 10) & (iki < 60000)]
        if len(iki) < MIN_EVENTS:
            continue

        # Per-writer entropy
        quantized = (iki // QUANTIZATION_MS) * QUANTIZATION_MS
        probs = quantized.value_counts(normalize=True).values
        entropy = -np.sum(probs * np.log2(probs + 1e-15))

        # Per-writer CLC
        df["iki_ms"] = df["DownTime"].diff()
        df["cog"] = df["Activity"].map(COGNITIVE_LOAD).fillna(1)
        valid = df.dropna(subset=["iki_ms"])
        valid = valid[(valid["iki_ms"] > 10) & (valid["iki_ms"] < 60000)]
        clc_rho = np.nan
        if len(valid) >= 30 and valid["cog"].std() > 0:
            clc_rho, _ = stats.spearmanr(valid["cog"], valid["iki_ms"])

        iki_var = np.log(iki.var(ddof=0) + 1)
        pause_freq = (iki > 2000).mean()

        records.append({
            "writer_id": wid, "entropy": entropy,
            "clc_rho": clc_rho, "iki_log_var": iki_var, "pause_freq": pause_freq,
        })

        # Sliding-window: composition vs transcription
        if len(valid) < 60:
            continue
        WINDOW, STEP = 50, 25
        for start in range(0, len(valid) - WINDOW, STEP):
            w = valid.iloc[start:start + WINDOW]
            act_counts = w["Activity"].value_counts()
            n_input = act_counts.get("Input", 0)
            n_nonprod = act_counts.get("Nonproduction", 0)
            n_remove = act_counts.get("Remove/Cut", 0)
            comp_frac = (n_nonprod + n_remove) / WINDOW
            input_frac = n_input / WINDOW

            if comp_frac >= 0.3:
                label = "composition"
            elif input_frac >= 0.8:
                label = "transcription"
            else:
                continue

            w_iki = w["iki_ms"].values
            w_cog = w["cog"].values
            w_rho = np.nan
            if w_cog.std() > 0:
                w_rho, _ = stats.spearmanr(w_cog, w_iki)

            w_quant = (pd.Series(w_iki) // QUANTIZATION_MS * QUANTIZATION_MS)
            w_probs = w_quant.value_counts(normalize=True).values
            w_entropy = -np.sum(w_probs * np.log2(w_probs + 1e-15))

            window_records.append({
                "writer_id": wid, "label": label,
                "clc_rho": w_rho, "entropy": w_entropy,
            })

    df_feat = pd.DataFrame(records).dropna()
    df_windows = pd.DataFrame(window_records).dropna()
    log.info(f"  Writers with complete features: {len(df_feat)}")
    n_comp = len(df_windows[df_windows.label == "composition"])
    n_trans = len(df_windows[df_windows.label == "transcription"])
    log.info(f"  Windows: {len(df_windows)} (composition={n_comp}, transcription={n_trans})")

    # --- 6b. Figure 1: CLC Distribution ---
    log.info("\n  [6b] Figure 1: Per-Writer CLC Distribution...")
    fig, ax = plt.subplots(figsize=(5.5, 3.5))
    clc_vals = df_feat["clc_rho"].values
    pct_pos = (clc_vals > 0).mean() * 100

    bins = np.linspace(clc_vals.min() - 0.02, clc_vals.max() + 0.02, 60)
    n_hist, bin_edges, patches = ax.hist(
        clc_vals, bins=bins, color="#4878CF", edgecolor="white", linewidth=0.3, alpha=0.85
    )
    for patch, left_edge in zip(patches, bin_edges[:-1]):
        if left_edge + (bin_edges[1] - bin_edges[0]) / 2 < 0:
            patch.set_facecolor("#E24A33")
            patch.set_alpha(0.7)
    ax.axvline(0.15, color="black", linestyle="--", linewidth=1.0, label=r"$\tau = 0.15$")
    ax.axvline(0, color="gray", linestyle=":", linewidth=0.8)
    ax.set_xlabel(r"Per-Writer CLC (Spearman $\rho$)")
    ax.set_ylabel("Number of Writers")
    ax.set_title("Per-Writer Cognitive-Load Correlation Distribution")
    ax.legend(frameon=False)
    fig.savefig(fig_dir / "fig_clc_distribution.pdf")
    fig.savefig(fig_dir / "fig_clc_distribution.png")
    plt.close(fig)
    log.info("    Saved figures/fig_clc_distribution.{pdf,png}")

    # --- 6c. Figure 2: Correlation Matrix ---
    log.info("\n  [6c] Figure 2: Correlation Matrix Heatmap...")
    features = ["entropy", "clc_rho", "iki_log_var", "pause_freq"]
    labels = ["Entropy", "CLC", r"IKI $\log$ Var", "Pause Freq"]
    n_f = len(features)
    corr_mat = np.ones((n_f, n_f))
    for i in range(n_f):
        for j in range(n_f):
            if i != j:
                rho, _ = stats.spearmanr(df_feat[features[i]], df_feat[features[j]])
                corr_mat[i, j] = rho

    fig, ax = plt.subplots(figsize=(4.5, 4.0))
    cax = ax.imshow(corr_mat, cmap="RdBu_r", vmin=-1, vmax=1, aspect="equal")
    for i in range(n_f):
        for j in range(n_f):
            color = "white" if abs(corr_mat[i, j]) > 0.5 else "black"
            ax.text(j, i, f"{corr_mat[i,j]:.2f}", ha="center", va="center",
                    fontsize=10, color=color, fontweight="bold")
    ax.set_xticks(range(n_f))
    ax.set_yticks(range(n_f))
    ax.set_xticklabels(labels, rotation=35, ha="right")
    ax.set_yticklabels(labels)
    ax.set_title(f"Cross-Domain Correlation Matrix (N={len(df_feat):,} Writers)", pad=12)
    fig.colorbar(cax, ax=ax, fraction=0.046, pad=0.04, label=r"Spearman $\rho$")
    fig.savefig(fig_dir / "fig_correlation_matrix.pdf")
    fig.savefig(fig_dir / "fig_correlation_matrix.png")
    plt.close(fig)
    log.info("    Saved figures/fig_correlation_matrix.{pdf,png}")

    # --- 6d. Figure 3: Composition vs Transcription ---
    log.info("\n  [6d] Figure 3: Composition vs Transcription CLC...")
    comp = df_windows[df_windows.label == "composition"]["clc_rho"].values
    trans = df_windows[df_windows.label == "transcription"]["clc_rho"].values
    comp_ent = df_windows[df_windows.label == "composition"]["entropy"].values
    trans_ent = df_windows[df_windows.label == "transcription"]["entropy"].values

    fig, axes = plt.subplots(1, 2, figsize=(8, 3.5))
    bins_c = np.linspace(-0.8, 0.8, 50)
    axes[0].hist(comp, bins=bins_c, alpha=0.65, color="#4878CF", label="Composition",
                 density=True, edgecolor="white", linewidth=0.3)
    axes[0].hist(trans, bins=bins_c, alpha=0.65, color="#E24A33", label="Transcription",
                 density=True, edgecolor="white", linewidth=0.3)
    axes[0].set_xlabel(r"Window CLC (Spearman $\rho$)")
    axes[0].set_ylabel("Density")
    axes[0].set_title("A. CLC Distributions by Mode")
    axes[0].legend(frameon=False)

    bins_e = np.linspace(
        min(comp_ent.min(), trans_ent.min()) - 0.2,
        max(comp_ent.max(), trans_ent.max()) + 0.2, 50
    )
    axes[1].hist(comp_ent, bins=bins_e, alpha=0.65, color="#4878CF", label="Composition",
                 density=True, edgecolor="white", linewidth=0.3)
    axes[1].hist(trans_ent, bins=bins_e, alpha=0.65, color="#E24A33", label="Transcription",
                 density=True, edgecolor="white", linewidth=0.3)
    axes[1].set_xlabel("Window Entropy (bits)")
    axes[1].set_ylabel("Density")
    axes[1].set_title("B. Entropy Distributions by Mode")
    axes[1].legend(frameon=False)

    fig.suptitle("Composition vs Transcription-like Windows", y=1.02, fontsize=12)
    fig.tight_layout()
    fig.savefig(fig_dir / "fig_clc_composition_vs_transcription.pdf")
    fig.savefig(fig_dir / "fig_clc_composition_vs_transcription.png")
    plt.close(fig)
    log.info("    Saved figures/fig_clc_composition_vs_transcription.{pdf,png}")

    # --- 6e. Effect sizes ---
    log.info("\n  [6e] Computing effect sizes...")

    def cohens_d(a, b):
        na, nb = len(a), len(b)
        pooled = np.sqrt(((na-1)*a.std(ddof=1)**2 + (nb-1)*b.std(ddof=1)**2) / (na+nb-2))
        return (a.mean() - b.mean()) / pooled if pooled > 0 else 0.0

    def glass_delta(a, b):
        return (a.mean() - b.mean()) / b.std(ddof=1) if b.std(ddof=1) > 0 else 0.0

    def cliffs_delta(a, b):
        u_stat, _ = stats.mannwhitneyu(a, b, alternative="two-sided")
        return 1 - (2 * u_stat) / (len(a) * len(b))

    effects = {
        "n_composition_windows": int(len(comp)),
        "n_transcription_windows": int(len(trans)),
    }

    for metric_name, comp_vals, trans_vals in [
        ("entropy", comp_ent, trans_ent),
        ("clc", comp, trans),
    ]:
        cd = cohens_d(comp_vals, trans_vals)
        gd = glass_delta(comp_vals, trans_vals)
        cld = cliffs_delta(comp_vals, trans_vals)
        mw_p = stats.mannwhitneyu(comp_vals, trans_vals).pvalue

        magnitude = ("large" if abs(cd) >= 0.8 else "medium" if abs(cd) >= 0.5
                      else "small" if abs(cd) >= 0.2 else "negligible")

        effects[metric_name] = {
            "composition_mean": round(float(comp_vals.mean()), 4),
            "composition_sd": round(float(comp_vals.std(ddof=1)), 4),
            "transcription_mean": round(float(trans_vals.mean()), 4),
            "transcription_sd": round(float(trans_vals.std(ddof=1)), 4),
            "cohens_d": round(float(cd), 4),
            "glass_delta": round(float(gd), 4),
            "cliffs_delta": round(float(cld), 4),
            "mann_whitney_p": float(f"{mw_p:.4e}"),
            "magnitude": magnitude,
        }

        log.info(f"\n  {metric_name.upper()}:")
        log.info(f"    Cohen's d:  {cd:.4f} ({magnitude})")
        log.info(f"    Glass's D:  {gd:.4f}")
        log.info(f"    Cliff's d:  {cld:.4f}")
        log.info(f"    Mann-Whitney p: {mw_p:.4e}")

    results["effect_sizes"] = effects
    return results


# ============================================================================
# STAGE 7: Summary Report
# ============================================================================
def stage_summary(all_results):
    """Print consolidated summary and save results."""
    log.info("\n" + "=" * 72)
    log.info("STAGE 7: Summary Report")
    log.info("=" * 72)

    log.info("\n  Paper Claims vs. Empirical Results:")
    log.info("  " + "-" * 68)

    sw = all_results.get("scholawrite", {})
    kl = all_results.get("klicke", {})
    roc = all_results.get("roc", {})
    eff = all_results.get("effects", {}).get("effect_sizes", {})

    # ScholaWrite entropy
    sw_ent = sw.get("entropy_per_iki_bits")
    if sw_ent is not None:
        status = "CLOSE" if abs(sw_ent - 10.4) < 2.0 else "DIFFERS"
        log.info(f"  ScholaWrite entropy:      {sw_ent:.2f} bits (paper claim: ~10.4 bits) [{status}]")

    # CLC Cohen's d
    sw_cd = sw.get("disc_cohens_d")
    if sw_cd is not None:
        status = "CLOSE" if abs(sw_cd - 1.82) < 1.0 else "DIFFERS"
        log.info(f"  CLC Cohen's d:            {sw_cd:.2f} (paper claim: ~1.82) [{status}]")

    # KLiCKe effect sizes
    if "clc" in eff:
        clc_d = eff["clc"].get("cohens_d")
        if clc_d is not None:
            log.info(f"  KLiCKe CLC Cohen's d:     {clc_d:.4f} ({eff['clc'].get('magnitude', '')})")

    # ROC AUC
    all_atk = roc.get("all_attacks", {})
    if all_atk:
        auc_val = all_atk.get("auc")
        if auc_val is not None:
            status = "CLOSE" if abs(auc_val - 0.78) < 0.15 else "DIFFERS"
            log.info(f"  Classification AUC:       {auc_val:.4f} (paper claim: ~0.78) [{status}]")
        eer_val = all_atk.get("eer")
        if eer_val is not None:
            log.info(f"  EER:                      {eer_val:.4f}")

    # Feature importance
    fi = roc.get("feature_importance")
    if fi:
        log.info("\n  Feature Importance (|coef|, logistic regression):")
        for feat in sorted(fi, key=fi.get, reverse=True):
            log.info(f"    {feat:18s}: {fi[feat]:.4f}")

    # KLiCKe population stats
    if kl:
        log.info("\n  KLiCKe Population Statistics:")
        log.info(f"    Writers:          {kl.get('n_writers', 'N/A'):,}")
        log.info(f"    Valid IKIs:       {kl.get('valid_ikis', 'N/A'):,}")
        log.info(f"    Mean IKI:         {kl.get('iki_mean_ms', 0):.1f} ms")
        log.info(f"    Entropy/IKI:      {kl.get('entropy_per_iki_bits', 0):.2f} bits")
        log.info(f"    Per-writer CLC:   mean rho={kl.get('clc_per_writer_mean_rho', 0):.4f}")
        log.info(f"    Positive CLC:     {kl.get('clc_pct_positive', 0):.1f}%%")

    # Save results
    script_dir = Path(__file__).resolve().parent
    output_path = script_dir / "analysis_results.json"
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    log.info(f"\n  Results saved to {output_path}")

    log.info("\n" + "=" * 72)
    log.info("ANALYSIS COMPLETE")
    log.info("=" * 72)


# ============================================================================
# MAIN
# ============================================================================
def main():
    import numpy as np
    np.random.seed(42)
    random.seed(42)

    all_results = {}
    total_start = time.time()

    # Stage 1: Environment Check
    t0 = time.time()
    has_klicke, klicke_format = stage_environment_check()
    log.info(f"\n  Stage 1 completed in {time.time() - t0:.1f}s")

    # Stage 2: ScholaWrite Analysis (always runs)
    t0 = time.time()
    all_results["scholawrite"] = stage_scholawrite()
    log.info(f"\n  Stage 2 completed in {time.time() - t0:.1f}s")

    # Stages 3-6: KLiCKe-dependent
    if has_klicke:
        # Stage 3: KLiCKe Analysis
        t0 = time.time()
        klicke_results, df_klicke, writer_valid, df_wclc, writer_clc_proxy = stage_klicke(klicke_format)
        all_results["klicke"] = klicke_results
        log.info(f"\n  Stage 3 completed in {time.time() - t0:.1f}s")

        # Stage 4: Retype Simulation
        t0 = time.time()
        retype_results, df_sessions = stage_retype_simulation(df_klicke)
        all_results["retype"] = retype_results
        log.info(f"\n  Stage 4 completed in {time.time() - t0:.1f}s")

        # Stage 5: ROC Classification
        t0 = time.time()
        all_results["roc"] = stage_roc_classification()
        log.info(f"\n  Stage 5 completed in {time.time() - t0:.1f}s")

        # Stage 6: Effect Sizes and Figures
        t0 = time.time()
        all_results["effects"] = stage_effect_sizes_and_figures(df_klicke)
        log.info(f"\n  Stage 6 completed in {time.time() - t0:.1f}s")
    else:
        log.info("\n  Stages 3-6 skipped (KLiCKe data not available)")
        log.info("  ScholaWrite-only results are still valid and complete.")

    # Stage 7: Summary
    stage_summary(all_results)

    total_elapsed = time.time() - total_start
    log.info(f"\n  Total elapsed time: {total_elapsed:.1f}s")


if __name__ == "__main__":
    main()
