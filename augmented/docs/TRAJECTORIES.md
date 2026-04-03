# Injection Trajectories and Boundary Erosion

## 1) Overview

A **trajectory** describes how an externally inserted span evolves across subsequent revisions. Trajectories model the degree to which inserted content becomes integrated into the surrounding text, causing boundary erosion and increasing annotation ambiguity.

Trajectories are a core component of the ScholaWrite-Augmented annotation schema and directly inform the `ambiguity_flag` assigned to each span.

## 2) Trajectory States

### 2.1 Cold

The inserted span remains **unchanged** across all subsequent revisions.

Properties:
- No edits to the inserted text after initial placement.
- Boundaries remain sharp and unambiguous.
- Stylistic discontinuity (if any) persists.
- Ambiguity flag: typically `none` or `low`.

Example: a paragraph pasted verbatim that is never revised.

### 2.2 Warm

The inserted span undergoes **light editing** in subsequent revisions.

Properties:
- Minor modifications: typo fixes, word substitutions, punctuation changes.
- Boundaries remain largely identifiable but may blur at edges.
- Some stylistic alignment with surrounding text may occur.
- Ambiguity flag: typically `low` or `medium`.

Example: a pasted paragraph where the author later fixes a few word choices to match surrounding tone.

### 2.3 Assimilated

The inserted span undergoes **substantial revision** across multiple revision steps.

Properties:
- Significant rewriting, restructuring, or fragmentation of the original insertion.
- Boundaries erode substantially; original span may no longer be contiguous.
- Stylistic alignment with surrounding text is high.
- Attribution becomes increasingly indeterminate.
- Ambiguity flag: typically `medium` or `high`.

Example: a pasted paragraph that the author rewrites across three revisions, blending it with their own additions until the boundary is unclear.

## 3) State Transition Rules

Trajectories follow a **monotonic erosion** model:

```
cold → warm → assimilated
```

Constraints:
- Transitions are **irreversible**: once a span moves to a warmer state, it cannot revert.
- Each transition requires at least one revision with observable edits to the span.
- The transition is recorded with the revision index at which it occurs.

State machine:

```
┌──────┐   edit    ┌──────┐   substantial   ┌─────────────┐
│ cold │ ────────→ │ warm │ ──────────────→  │ assimilated │
└──────┘           └──────┘                  └─────────────┘
   │                                              ▲
   └──────────── substantial edit ────────────────┘
```

A cold span may transition directly to assimilated if the first edit is substantial.

## 4) Edit Classification

Edits to injected spans are classified for trajectory purposes:

| Edit Type | Classification | Transition |
|-----------|---------------|------------|
| No change | None | Stays in current state |
| Typo fix, punctuation | Light | cold → warm |
| Word substitution (< 20% tokens) | Light | cold → warm |
| Sentence rewrite | Substantial | warm → assimilated |
| Reordering or fragmentation | Substantial | warm → assimilated |
| Token change >= 20% | Substantial | cold/warm → assimilated |

Thresholds:
- **Light edit**: < 20% of tokens in the span are modified.
- **Substantial edit**: >= 20% of tokens modified, or structural changes (sentence splits, reordering).

## 5) Ambiguity Flag Assignment

The ambiguity flag reflects confidence in boundary determination:

| Trajectory State | Typical Ambiguity | Rationale |
|-----------------|-------------------|-----------|
| cold | none | Boundaries are exact; no edits occurred |
| cold (stylistically coherent) | low | Insertion is detectable only by process, not style |
| warm | low–medium | Edges may have shifted slightly |
| assimilated (partial) | medium | Boundaries are approximate |
| assimilated (extensive) | high | Original boundary is indeterminate |

The ambiguity flag is a **required field** in all annotation records and must be justified by the trajectory state and edit history.

## 6) Boundary Erosion Model

Boundary erosion is the process by which an injection's start and end offsets become unreliable indicators of the original insertion:

1. **Edge erosion**: edits at the boundaries of the injected span (beginning/end) blur the transition points.
2. **Internal fragmentation**: the span is split by new author-written content inserted within it.
3. **Stylistic assimilation**: the span's language converges with surrounding text, making boundary placement arbitrary.

When boundaries erode, annotations must:
- Update `span_start_char` and `span_end_char` to best-effort estimates.
- Set `ambiguity_flag` to reflect the uncertainty.
- Preserve the original offsets in a `original_span_start` / `original_span_end` field for reference.

## 7) Implementation Reference

Trajectory state enum is defined in `src/scholawrite/schema.py`:
- `TrajectoryState` enum: `COLD`, `WARM`, `ASSIMILATED`

Trajectory logic is implemented in `src/scholawrite/trajectories.py`:
- `compute_transition(span, revision_edits)`: determines state change.
- `apply_trajectory(injection_span, revisions)`: computes final trajectory and ambiguity.
- `classify_edit(old_tokens, new_tokens)`: returns `light` or `substantial`.

Ambiguity validation is implemented in `src/scholawrite/annotations.py`:
- `validate_earned_ambiguity(span, subsequent_revisions)`: verifies ambiguity flag is supported by causal evidence and boundary erosion.
- `compute_boundary_erosion(original_span, subsequent_revisions)`: measures boundary shift ratio across revisions.

## 8) Relationship to Other Components

- **Annotations** (`src/scholawrite/annotations.py`): trajectory state is a required annotation field.
- **Augmentation** (`src/scholawrite/augment.py`): trajectories are applied during augmented document construction.
- **Label Taxonomy** (`docs/LABEL_TAXONOMY.md`): trajectory states are orthogonal to injection levels.
- **Protocol** (`docs/PROTOCOL.md`): Section 6 references this document.

## 9) Validation

Trajectory assignments are validated by:
- `scripts/validate_annotations.py`: ensures trajectory state is consistent with edit history.
- `tests/test_trajectories.py`: unit tests for state transitions and edge cases.
- Ambiguity flags must be present for all warm/assimilated spans (enforced in CI).

### 9.1 Boundary Erosion Validation

In addition to causal signatures, ambiguity flags are validated using **boundary erosion**—a measure of how much span boundaries shift across revisions. This provides an independent verification that claimed ambiguity levels reflect actual annotation difficulty.

Boundary erosion is computed as:
```
erosion = avg_boundary_shift / original_span_size
```

Where `avg_boundary_shift` is the mean total shift (start + end) across subsequent revisions.

| Ambiguity Flag | Minimum Erosion | Rationale |
|----------------|-----------------|-----------|
| none | 0.0 | No edits, boundaries unchanged |
| low | — | Erosion not required (causal trace suffices) |
| medium | 0.1 | Boundaries shifted by at least 10% of span size |
| high | 0.25 | Boundaries shifted by at least 25% of span size |

Implementation: `validate_earned_ambiguity()` and `compute_boundary_erosion()` in `src/scholawrite/annotations.py`.
