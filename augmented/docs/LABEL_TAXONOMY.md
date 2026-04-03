# Label Taxonomy

## 1) Purpose

This document defines the label namespaces, hierarchy, and disjointness rules for all annotations in ScholaWrite-Augmented. Labels describe **process events and states**, not origin or intent.

All labels must conform to this taxonomy. Validation is enforced by `scripts/lint_data.py`.

## 2) Namespaces

| Namespace | Description | Scope |
|-----------|-------------|-------|
| `injection.*` | External insertion events | Spans introduced from outside the revision process |
| `anomaly.*` | Process anomalies (non-injective) | Revision-level irregularities unrelated to insertion |
| `assistance.*` | Process-consistent assistance | Tool use visibly integrated through revisions |

## 3) Injection Labels

Labels for externally inserted spans, qualified by sophistication level:

| Label | Description | Reference |
|-------|-------------|-----------|
| `injection.naive` | Topic-agnostic or loosely related insertion | `docs/INJECTION_LEVELS.md` Section 2.1 |
| `injection.topical` | Same-domain but context-agnostic insertion | `docs/INJECTION_LEVELS.md` Section 2.2 |
| `injection.contextual` | Locally coherent, context-aligned insertion | `docs/INJECTION_LEVELS.md` Section 2.3 |

## 4) Anomaly Labels

Labels for process-level irregularities that are **not** external insertions:

| Label | Description | Characteristics |
|-------|-------------|-----------------|
| `anomaly.missing_revision` | Gap in expected revision sequence | Revision indices skip; no intermediate state |
| `anomaly.timestamp_jitter` | Implausible timestamp ordering or spacing | Timestamps out of order or unrealistically close/far |
| `anomaly.truncation` | Revision text appears truncated | Content ends mid-sentence or mid-paragraph |
| `anomaly.large_diff` | Unusually large single-revision change | Diff size exceeds expected thresholds without intermediates |
| `anomaly.process_violation` | Spatially disjoint repair patterns | Locality signature exceeds human baseline threshold |
| `anomaly.no_resource_coupling` | Absence of human production signatures | Coupling signature below minimum human baseline threshold |

## 5) Assistance Labels

Labels for process-consistent external tool use:

| Label | Description | Characteristics |
|-------|-------------|-----------------|
| `assistance.revision_assisted` | Content shows iterative integration of external input | Multiple revisions refine externally suggested content |

## 6) Required Annotation Fields

Every annotation record must include:

| Field | Type | Values | Description |
|-------|------|--------|-------------|
| `label` | string | Full namespace label (e.g., `injection.naive`) | Primary classification |
| `injection_level` | string | `naive` / `topical` / `contextual` | Injection sophistication (injection.* only) |
| `trajectory_state` | string | `cold` / `warm` / `assimilated` | Boundary erosion state (injection.* only) |
| `ambiguity_flag` | string | `none` / `low` / `medium` / `high` | Confidence in boundary determination |

For anomaly labels, `injection_level` and `trajectory_state` are set to `null`.

## 7) Disjointness Rules

### Hard constraints (enforced by validation):
- `injection.*` labels MUST NOT co-occur with `anomaly.*` labels on the same span.
- A single span MUST have exactly one `injection.*` label (no multi-level spans).
- `anomaly.*` labels apply at the revision level, not span level.

### Soft constraints (flagged for review):
- `assistance.*` MAY co-occur with `injection.*` only if explicitly flagged with `ambiguity_flag` >= `medium`.
- This represents cases where the boundary between assisted writing and injection is genuinely unclear.

## 8) Label Hierarchy

```
root
├── injection
│   ├── injection.naive
│   ├── injection.topical
│   └── injection.contextual
├── anomaly
│   ├── anomaly.missing_revision
│   ├── anomaly.timestamp_jitter
│   ├── anomaly.truncation
│   ├── anomaly.large_diff
│   ├── anomaly.process_violation
│   └── anomaly.no_resource_coupling
└── assistance
    └── assistance.revision_assisted
```

## 9) JSON Schema Fragment

Annotation records must validate against:

```json
{
  "label": {
    "type": "string",
    "enum": [
      "injection.naive",
      "injection.topical",
      "injection.contextual",
      "anomaly.missing_revision",
      "anomaly.timestamp_jitter",
      "anomaly.truncation",
      "anomaly.large_diff",
      "anomaly.process_violation",
      "anomaly.no_resource_coupling",
      "assistance.revision_assisted"
    ]
  },
  "injection_level": {
    "type": ["string", "null"],
    "enum": ["naive", "topical", "contextual", null]
  },
  "trajectory_state": {
    "type": ["string", "null"],
    "enum": ["cold", "warm", "assimilated", null]
  },
  "ambiguity_flag": {
    "type": "string",
    "enum": ["none", "low", "medium", "high"]
  }
}
```

## 10) Extension Policy

New labels may be added to the taxonomy only if:
1. They are recorded in `docs/NOTES.md` with rationale.
2. They do not violate the terminology contract (`docs/TERMINOLOGY.md`).
3. They maintain disjointness with existing namespaces.
4. Validation code (`scripts/lint_data.py`) is updated accordingly.
5. Tests are added to cover the new label.

## 11) Relationship to Other Documents

- **Terminology** (`docs/TERMINOLOGY.md`): labels must not imply origin or intent.
- **Protocol** (`docs/PROTOCOL.md`): Section 7 specifies annotation schema fields.
- **Injection Levels** (`docs/INJECTION_LEVELS.md`): defines the injection.* level semantics.
- **Trajectories** (`docs/TRAJECTORIES.md`): defines trajectory state semantics.
- **Schema** (`src/scholawrite/schema.py`): implements the label enum and validation.
