from __future__ import annotations
import pytest
from scripts.pii_scan import scan_text

def test_scan_text_empty():
    assert scan_text("") == []

def test_scan_text_clean():
    assert scan_text("This is a clean sentence with no PII.") == []

def test_scan_text_email():
    text = "Contact me at test@example.com for details."
    findings = scan_text(text)
    assert len(findings) == 1
    assert findings[0]["rule_id"] == "email"
    # Snippet logic: ... + text[start-10:end+10] + ...
    # "test@example.com" start=14, end=30
    # text[4:40] -> "act me at test@example.com for detai"
    assert findings[0]["snippet"] == "...act me at test@example.com for detai..."

def test_scan_text_phone():
    text = "Call 555-123-4567 today!"
    findings = scan_text(text)
    assert len(findings) == 1
    assert findings[0]["rule_id"] == "phone"

def test_scan_text_ssn():
    text = "My SSN is 123-45-6789."
    findings = scan_text(text)
    assert len(findings) == 1
    assert findings[0]["rule_id"] == "ssn"
    assert findings[0]["severity"] == "high"

def test_scan_text_multiple():
    text = "Email test@test.com or call 123-456-7890."
    findings = scan_text(text)
    assert len(findings) == 2
    rule_ids = {f["rule_id"] for f in findings}
    assert "email" in rule_ids
    assert "phone" in rule_ids
