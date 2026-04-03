"""I/O utilities for reading and writing ScholaWrite datasets."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import List, Union

import pandas as pd

from .schema import (
    AmbiguityFlag,
    AugmentedDocument,
    AugmentedRevision,
    InjectionLevel,
    InjectionSpan,
    Label,
    SeedDocument,
    SeedRevision,
    TrajectoryState,
    CausalEvent,
    GenerationMetadata,
)
from . import ids, text, time

__all__ = [
    "load_seed",
    "load_parquet_dir",
    "load_seed_split",
    "write_documents_jsonl",
    "read_documents_jsonl",
    "write_augmented_jsonl",
    "read_augmented_jsonl",
]

def load_parquet_dir(path: Union[str, Path], pattern: str = "*.parquet") -> pd.DataFrame:
    path = Path(path)
    if not path.exists(): raise FileNotFoundError(f"Path does not exist: {path}")
    if path.is_file() and path.suffix == ".parquet": return pd.read_parquet(path)
    parquet_files = list(path.glob(pattern)) or list(path.glob("**/*.parquet"))
    if not parquet_files: raise FileNotFoundError(f"No parquet files found in: {path}")
    dfs = [pd.read_parquet(f) for f in sorted(parquet_files)]
    return pd.concat(dfs, ignore_index=True)

def _build_documents_from_df(df: pd.DataFrame) -> List[SeedDocument]:
    documents = []
    for project_id, group in df.groupby("project"):
        group_sorted = group.sort_values("timestamp").reset_index(drop=True)
        doc_id = ids.make_doc_id(f"scholawrite:project:{project_id}")
        revisions = []
        for revision_index, row in group_sorted.iterrows():
            # Extract after text (current state)
            raw_text = str(row["after text"]) if not pd.isna(row.get("after text")) else ""
            norm_text = text.normalize_text(raw_text)

            # Extract before text (previous state for diff)
            raw_before = str(row["before text"]) if not pd.isna(row.get("before text")) else None
            norm_before = text.normalize_text(raw_before) if raw_before else None

            # Extract original ScholaWrite annotations
            writing_intention = str(row["label"]) if not pd.isna(row.get("label")) else None
            high_level = str(row["high-level"]) if not pd.isna(row.get("high-level")) else None

            revisions.append(SeedRevision(
                doc_id=doc_id,
                revision_id=ids.make_revision_id(doc_id, int(revision_index)),
                revision_index=int(revision_index),
                text=norm_text,
                timestamp=time.normalize_timestamp(row.get("timestamp")),
                provenance_hash=text.compute_provenance_hash(norm_text),
                before_text=norm_before,
                writing_intention=writing_intention,
                high_level_category=high_level,
            ))
        documents.append(SeedDocument(doc_id=doc_id, revisions=revisions))
    documents.sort(key=lambda d: d.doc_id)
    return documents

def load_seed(path: Union[str, Path]) -> List[SeedDocument]:
    df = load_parquet_dir(path)
    return _build_documents_from_df(df)

VALID_SPLITS = {"train", "val", "test", "test_small", "train_small", "val_small"}

def load_seed_split(base_path: Union[str, Path], split: str = "test_small") -> List[SeedDocument]:
    if split not in VALID_SPLITS:
        raise ValueError(f"Invalid split: '{split}'. Must be one of: {sorted(VALID_SPLITS)}")
    base_path = Path(base_path)
    data_dir = base_path / "data" if (base_path / "data").exists() else base_path
    pattern = f"{split}-*.parquet"
    parquet_files = list(data_dir.glob(pattern))
    if not parquet_files: raise FileNotFoundError(f"No parquet for split '{split}' in {data_dir}")
    dfs = [pd.read_parquet(f) for f in sorted(parquet_files)]
    return _build_documents_from_df(pd.concat(dfs, ignore_index=True))

def write_documents_jsonl(documents: List[SeedDocument], output_path: Union[str, Path]) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for doc in documents:
            f.write(json.dumps(asdict(doc), ensure_ascii=False) + "\n")

def read_documents_jsonl(input_path: Union[str, Path]) -> List[SeedDocument]:
    input_path = Path(input_path)
    if not input_path.exists(): raise FileNotFoundError(f"Input not found: {input_path}")
    documents = []
    total_revs = 0
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            data = json.loads(line)
            revisions = []
            for rev in data["revisions"]:
                revisions.append(SeedRevision(
                    doc_id=rev["doc_id"],
                    revision_id=rev["revision_id"],
                    revision_index=rev["revision_index"],
                    text=rev["text"],
                    timestamp=rev.get("timestamp"),
                    provenance_hash=rev["provenance_hash"],
                    # Original ScholaWrite fields (may be None for older data)
                    before_text=rev.get("before_text"),
                    writing_intention=rev.get("writing_intention"),
                    high_level_category=rev.get("high_level_category"),
                ))
            total_revs += len(revisions)
            if total_revs % 10000 == 0: print(f"Loaded {total_revs} revisions...")
            documents.append(SeedDocument(doc_id=data["doc_id"], revisions=revisions))
    return documents

def _serialize_enum(value):
    return value.value if hasattr(value, "value") else value

def _serialize_injection_span(span: InjectionSpan) -> dict:
    d = {
        "doc_id": span.doc_id, "revision_id": span.revision_id, "injection_id": span.injection_id,
        "injection_level": _serialize_enum(span.injection_level),
        "trajectory_state": _serialize_enum(span.trajectory_state),
        "ambiguity_flag": _serialize_enum(span.ambiguity_flag),
        "span_start_char": span.span_start_char, "span_end_char": span.span_end_char,
        "span_start_sentence": span.span_start_sentence, "span_end_sentence": span.span_end_sentence,
        "generator_class": span.generator_class, "prompt_hash": span.prompt_hash,
        "rng_seed": span.rng_seed, "provenance_hash": span.provenance_hash,
        "label": _serialize_enum(span.label),
        "original_start_char": span.original_start_char,
        "original_end_char": span.original_end_char,
        "biometric_salt": span.biometric_salt,
        "causal_trace": [asdict(e) for e in span.causal_trace],
        "generation_metadata": asdict(span.generation_metadata) if span.generation_metadata else None,
    }
    return d

def _serialize_augmented_document(doc: AugmentedDocument) -> dict:
    return {
        "doc_id": doc.doc_id,
        "revisions": [
            {
                "doc_id": r.doc_id, "revision_id": r.revision_id, "revision_index": r.revision_index,
                "text": r.text, "timestamp": r.timestamp, "provenance_hash": r.provenance_hash,
                "annotations": [_serialize_injection_span(ann) for ann in r.annotations],
                # Original ScholaWrite fields
                "before_text": r.before_text,
                "writing_intention": r.writing_intention,
                "high_level_category": r.high_level_category,
            }
            for r in doc.revisions
        ]
    }

def write_augmented_jsonl(documents: List[AugmentedDocument], output_path: Union[str, Path]) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "a", encoding="utf-8") as f:
        for doc in documents:
            f.write(json.dumps(_serialize_augmented_document(doc), ensure_ascii=False) + "\n")

def _deserialize_injection_span(data: dict) -> InjectionSpan:
    causal = [CausalEvent(**e) for e in data.get("causal_trace", [])]
    meta_data = data.get("generation_metadata")
    gen_meta = GenerationMetadata(**meta_data) if meta_data else None
    return InjectionSpan(
        doc_id=data["doc_id"], revision_id=data["revision_id"], injection_id=data["injection_id"],
        label=Label(data["label"]),
        injection_level=InjectionLevel(data["injection_level"]) if data["injection_level"] else None,
        trajectory_state=TrajectoryState(data["trajectory_state"]) if data["trajectory_state"] else None,
        ambiguity_flag=AmbiguityFlag(data["ambiguity_flag"]),
        span_start_char=data["span_start_char"], span_end_char=data["span_end_char"],
        span_start_sentence=data["span_start_sentence"], span_end_sentence=data["span_end_sentence"],
        generator_class=data["generator_class"], prompt_hash=data["prompt_hash"],
        rng_seed=data["rng_seed"], provenance_hash=data["provenance_hash"],
        original_start_char=data.get("original_start_char"),
        original_end_char=data.get("original_end_char"),
        biometric_salt=data.get("biometric_salt"),
        causal_trace=causal,
        generation_metadata=gen_meta,
    )

def read_augmented_jsonl(input_path: Union[str, Path]) -> List[AugmentedDocument]:
    input_path = Path(input_path)
    if not input_path.exists(): raise FileNotFoundError(f"Input not found: {input_path}")
    documents = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            data = json.loads(line)
            revisions = []
            for rev_data in data["revisions"]:
                annotations = [_deserialize_injection_span(ann) for ann in rev_data.get("annotations", [])]
                revisions.append(AugmentedRevision(
                    doc_id=rev_data["doc_id"], revision_id=rev_data["revision_id"],
                    revision_index=rev_data["revision_index"], text=rev_data["text"],
                    timestamp=rev_data["timestamp"], provenance_hash=rev_data["provenance_hash"],
                    annotations=annotations,
                    # Original ScholaWrite fields (may be None for older data)
                    before_text=rev_data.get("before_text"),
                    writing_intention=rev_data.get("writing_intention"),
                    high_level_category=rev_data.get("high_level_category"),
                ))
            documents.append(AugmentedDocument(doc_id=data["doc_id"], revisions=revisions))
    return documents
