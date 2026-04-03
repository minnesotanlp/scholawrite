"""ID generation utilities for documents, revisions, and injections."""
from __future__ import annotations

import hashlib
from typing import Dict, Any

__all__ = [
    "make_doc_id", "make_revision_id", "make_injection_id",
    "make_causal_injection_id", "make_author_id",
    "DOC_ID_PREFIX", "REV_ID_PREFIX", "INJ_ID_PREFIX",
]

# ID prefixes for different entity types
DOC_ID_PREFIX = "doc_"
REV_ID_PREFIX = "rev_"
INJ_ID_PREFIX = "inj_"

def _hash(val: str) -> str:
    """Stable 16-char SHA-256 hash."""
    return hashlib.sha256(val.encode("utf-8")).hexdigest()[:16]

def make_doc_id(source_id: str) -> str:
    return f"{DOC_ID_PREFIX}{_hash(source_id)}"

def make_revision_id(doc_id: str, index: int) -> str:
    return f"{REV_ID_PREFIX}{_hash(f'{doc_id}:{index}')}"

def make_injection_id(doc_id: str, revision_id: str, ordinal: int) -> str:
    """Create injection ID from structural position."""
    return f"{INJ_ID_PREFIX}{_hash(f'{doc_id}:{revision_id}:{ordinal}')}"

def make_author_id(doc_id: str) -> str:
    """Persistent author ID anchored to original document source."""
    return f"author_{_hash(doc_id)}"

def make_causal_injection_id(
    doc_id: str,
    rev_id: str,
    ordinal: int,
    sigs: Dict[str, Any]
) -> str:
    """
    Cryptographically bind ID to CAUSAL FINGERPRINT.
    locality: repair proximity (Human: 1-3 tokens)
    coupling: resource coupling (Human: r > 0.6)
    """
    locality = sigs.get("repair_locality", 0.0)
    coupling = sigs.get("resource_coupling", 0.0)
    fingerprint = f"{locality:.2f}:{coupling:.2f}"

    # Anchor to structural position AND the irreversible process fingerprint
    identity_blob = f"{doc_id}:{rev_id}:{ordinal}:{fingerprint}"
    return f"inj_{_hash(identity_blob)}"
