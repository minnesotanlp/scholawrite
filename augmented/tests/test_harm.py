from __future__ import annotations
import pytest
from scholawrite.harm import compute_harm
from scholawrite.schema import AugmentedDocument, AugmentedRevision, InjectionSpan, Label, InjectionLevel, TrajectoryState, AmbiguityFlag

def test_compute_harm_basic():
    # 1. Revision with anomaly.missing_revision (True Negative for injection, but let's see if predicted)
    # The baseline template matcher looks for placeholder templates.
    # "This is a general academic statement." is a NAIVE template.
    
    rev_anomaly = AugmentedRevision(
        "doc1", "rev1", 1, "Normal text.", "2026-01-27T00:00:00Z", "h1",
        [InjectionSpan("doc1", "rev1", "anom1", None, None, AmbiguityFlag.MEDIUM, 0, 11, 0, 0, "test", "h", 0, None, Label.ANOMALY_MISSING_REVISION)]
    )
    
    # 2. Revision with injection.naive (True Positive)
    rev_injection = AugmentedRevision(
        "doc2", "rev2", 1, "This is a general academic statement.", "2026-01-27T00:00:00Z", "h2",
        [InjectionSpan("doc2", "rev2", "inj1", InjectionLevel.NAIVE, TrajectoryState.COLD, AmbiguityFlag.NONE, 0, 36, 0, 0, "test", "h", 0, "p", Label.INJECTION_NAIVE)]
    )
    
    doc1 = AugmentedDocument("doc1", [rev_anomaly])
    doc2 = AugmentedDocument("doc2", [rev_injection])
    
    results = compute_harm([doc1, doc2])
    
    # doc1/rev1 has anomaly.missing_revision and text "Normal text." -> not predicted by template matcher -> FP=0 -> FPR=0
    assert results["fpr_anomaly_missing_revision"] == 0.0
    
    # doc2/rev2 has injection.naive and text matches template -> predicted -> TP=1 -> sensitivity=1.0
    assert results["sensitivity_level_naive"] == 1.0
    assert results["sensitivity_state_cold"] == 1.0

def test_compute_harm_false_positive():
    # Revision with anomaly that ALSO contains a template string (misidentification)
    rev = AugmentedRevision(
        "doc1", "rev1", 1, "This is a general academic statement.", "2026-01-27T00:00:00Z", "h1",
        [InjectionSpan("doc1", "rev1", "anom1", None, None, AmbiguityFlag.MEDIUM, 0, 36, 0, 0, "test", "h", 0, None, Label.ANOMALY_LARGE_DIFF)]
    )
    doc = AugmentedDocument("doc1", [rev])
    results = compute_harm([doc])
    
    # Predicted because of template text, but ground truth is ONLY anomaly -> FP
    assert results["fpr_anomaly_large_diff"] == 1.0