from __future__ import annotations
import pytest
from scholawrite.metrics import auc, f1, span_iou

def test_auc_perfect():
    y_true = [0, 0, 1, 1]
    y_score = [0.1, 0.4, 0.5, 0.8]
    assert auc(y_true, y_score) == 1.0

def test_auc_worst():
    y_true = [0, 0, 1, 1]
    y_score = [0.8, 0.5, 0.4, 0.1]
    assert auc(y_true, y_score) == 0.0

def test_auc_random():
    y_true = [0, 1]
    y_score = [0.5, 0.5]
    assert auc(y_true, y_score) == 0.5

def test_f1_perfect():
    assert f1([0, 1, 0, 1], [0, 1, 0, 1]) == 1.0

def test_f1_none():
    assert f1([0, 1, 0, 1], [1, 0, 1, 0]) == 0.0

def test_f1_partial():
    # tp=1, fp=1, fn=1 -> 2/ (2*1 + 1 + 1) = 2/4 = 0.5
    assert f1([1, 1, 0], [1, 0, 1]) == 0.5

def test_span_iou_perfect():
    spans = [(0, 10), (20, 30)]
    assert span_iou(spans, spans) == 1.0

def test_span_iou_no_overlap():
    assert span_iou([(0, 10)], [(10, 20)]) == 0.0

def test_span_iou_partial():
    # intersection 5, union 15
    assert span_iou([(0, 10)], [(5, 15)]) == 5/15