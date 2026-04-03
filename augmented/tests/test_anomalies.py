from __future__ import annotations
import pytest
from scholawrite.anomalies import _detect_revision_anomaly
from scholawrite.schema import AugmentedRevision, Label

def test_detect_anomaly_missing_revision():
    rev1 = AugmentedRevision("doc1", "rev1", 0, "Text", "2026-01-27T00:00:00Z", "h1", [])
    rev2 = AugmentedRevision("doc1", "rev2", 2, "Text", "2026-01-27T00:01:00Z", "h2", [])
    label = _detect_revision_anomaly([rev1, rev2], 1, [None, 60.0])
    assert label == Label.ANOMALY_MISSING_REVISION

def test_detect_anomaly_timestamp_jitter():
    rev1 = AugmentedRevision("doc1", "rev1", 0, "Text", "2026-01-27T00:01:00Z", "h1", [])
    rev2 = AugmentedRevision("doc1", "rev2", 1, "Text", "2026-01-27T00:00:00Z", "h2", [])
    label = _detect_revision_anomaly([rev1, rev2], 1, [None, -60.0])
    assert label == Label.ANOMALY_TIMESTAMP_JITTER

def test_detect_anomaly_truncation():
    text1 = "A very long sentence that provides enough content for truncation detection to work correctly in this test." * 5
    text2 = "A very long sentence"
    rev1 = AugmentedRevision("doc1", "rev1", 0, text1, "2026-01-27T00:00:00Z", "h1", [])
    rev2 = AugmentedRevision("doc1", "rev2", 1, text2, "2026-01-27T00:01:00Z", "h2", [])
    label = _detect_revision_anomaly([rev1, rev2], 1, [None, 60.0])
    assert label == Label.ANOMALY_TRUNCATION

def test_detect_anomaly_large_diff():
    text1 = "Sentence one. Sentence two. Sentence three. Sentence four. Sentence five."
    text2 = "Different vocabulary entirely. No shared words here. Completely new content."
    rev1 = AugmentedRevision("doc1", "rev1", 0, text1, "2026-01-27T00:00:00Z", "h1", [])
    rev2 = AugmentedRevision("doc1", "rev2", 1, text2, "2026-01-27T00:01:00Z", "h2", [])
    label = _detect_revision_anomaly([rev1, rev2], 1, [None, 60.0])
    assert label == Label.ANOMALY_LARGE_DIFF

def test_detect_no_anomaly():
    rev1 = AugmentedRevision("doc1", "rev1", 0, "Text content.", "2026-01-27T00:00:00Z", "h1", [])
    rev2 = AugmentedRevision("doc1", "rev2", 1, "Text content. Added.", "2026-01-27T00:01:00Z", "h2", [])
    label = _detect_revision_anomaly([rev1, rev2], 1, [None, 60.0])
    assert label is None
