# ScholaWrite Threshold Reference

This document provides a comprehensive reference for all threshold values used in the ScholaWrite codebase. Each threshold is documented with its value, location, and justification based on empirical research or design rationale.

## Overview

ScholaWrite uses thresholds to:
1. **Classify causal signatures** - Determine whether writing patterns match human biometric baselines
2. **Detect anomalies** - Identify process signature violations
3. **Classify trajectories** - Categorize injection evolution states (COLD/WARM/ASSIMILATED)
4. **Evaluate baselines** - Compute forensic detection metrics

---

## Causal Coupling Thresholds

These thresholds validate that trajectory labels are EARNED by measurable causal signatures.

| Threshold | Value | Used In | Justification |
|-----------|-------|---------|---------------|
| WARM minimum coupling | >= 0.40 | `trajectories.py:202` | Lower bound for emerging coupling; indicates partial biometric alignment without full assimilation. Based on observed range in incremental revision sessions. |
| ASSIMILATED minimum coupling | > 0.70 | `trajectories.py:198` | Strongest coupling threshold requiring both high coupling AND plausibility flag. Represents irreversible process integration. |
| ASSIMILATED validation coupling | >= 0.55 | `annotations.py:112` | Minimum coupling required to validate ASSIMILATED label during annotation checks. Lower than determination threshold to allow for measurement noise. |
| Human plausibility coupling | >= 0.60 | `causal_core.py:136`, `metrics.py:47` | Pearson r >= 0.6 between failure events and subsequent syntactic simplification. Based on cognitive science literature on resource-coupled writing behavior. |
| Anomaly no-coupling threshold | < 0.20 | `anomalies.py:81` | Injections with coupling below this threshold are flagged as ANOMALY_NO_COUPLING. Indicates absence of human production signatures. |
| Plausibility coupling (metrics) | > 0.50 | `metrics.py:47` | Slightly lower threshold used in general plausibility computation. Combined with locality constraint for overall determination. |

---

## Locality Thresholds

Repair locality measures the token distance between a failure event and its repair. Human writers exhibit characteristic repair patterns.

| Threshold | Value | Used In | Justification |
|-----------|-------|---------|---------------|
| Human repair locality range | 1.0 - 3.5 | `causal_core.py:121,136`, `metrics.py:22,47` | Based on typing repair studies showing humans typically repair errors within 1-3 tokens. Values outside this range indicate non-human production patterns. |
| WARM maximum locality | <= 4.5 | `trajectories.py:202` | Upper bound for WARM state classification. Allows slightly relaxed locality for partial integration. |
| Anomaly locality threshold | > 4.5 | `anomalies.py:79` | Locality exceeding human range triggers ANOMALY_PROCESS_VIOLATION. Indicates spatially disjoint repair patterns inconsistent with human cognition. |

---

## Edit Classification

These thresholds determine the magnitude of edits for trajectory state transitions.

| Threshold | Value | Used In | Justification |
|-----------|-------|---------|---------------|
| Substantial edit ratio | >= 0.20 | `trajectories.py:22,70` | 20% token change ratio classifies edit as SUBSTANTIAL rather than LIGHT. Based on analysis of revision patterns where 20% change typically indicates significant rewriting rather than minor corrections. |

---

## Detection Thresholds

Thresholds for statistical and forensic detection methods.

| Threshold | Value | Used In | Justification |
|-----------|-------|---------|---------------|
| NCD threshold (default) | 0.45 | `baselines.py:15,45` | Normalized Compression Distance threshold for anomaly detection. Empirically tuned to balance precision/recall for compression-based discontinuity detection. |
| NCD hardening delta | > 0.10 | `agentic.py:68` | If compression discontinuity between generated text and context exceeds this delta from baseline, triggers adversarial hardening pass. |
| Word Jaccard similarity (large diff) | < 0.30 | `anomalies.py:54` | Revisions with word-level Jaccard similarity below 30% are flagged as ANOMALY_LARGE_DIFF. Indicates potential wholesale replacement rather than revision. |
| Truncation threshold | < 0.40 | `anomalies.py:48` | If revision text length drops below 40% of previous (60%+ reduction), flagged as ANOMALY_TRUNCATION. |

---

## Embodied Simulation Thresholds

Parameters for the metabolic and cognitive simulation of scholarly writing.

### Glucose/Energy Thresholds

| Threshold | Value | Used In | Justification |
|-----------|-------|---------|---------------|
| Initial glucose | 1.0 | `embodied.py:20` | Full cognitive resources at session start. Normalized scale 0.0-1.0. |
| Minimum glucose floor | 0.05 | `causal_core.py:95,101`, `embodied.py:32` | Prevents complete resource depletion; maintains minimal cognitive function. |
| Glucose depletion rate | 0.9992 | `embodied.py:32` | Per-token logarithmic decay rate. Tuned to produce realistic fatigue curves over typical 90-minute writing sessions. |
| Lexical starvation glucose | < 0.65 | `causal_core.py:108` | Below this glucose level, high lexical rarity words trigger "lexical_starvation" failure mode. Based on resource competition models of lexical retrieval. |

### Fatigue and Latency Parameters

| Threshold | Value | Used In | Justification |
|-----------|-------|---------|---------------|
| Fatigue divisor | 12000.0 | `embodied.py:35` | Visual fatigue accumulates at tokens/12000.0 per token. Calibrated to reach significant fatigue (~0.5) after ~6000 tokens. |
| Maximum fatigue | 1.0 | `embodied.py:35` | Upper bound for visual fatigue index. |
| Base keystroke latency | 115 ms | `embodied.py:53` | Baseline inter-key interval. Based on typing studies showing ~100-150ms baseline latency. |
| Latency syntactic multiplier | 90 ms | `embodied.py:53` | Additional latency scaling based on syntactic complexity. Higher complexity = longer planning time. |
| Latency glucose factor | 1.12 | `embodied.py:53` | Glucose depletion increases latency through (1.12 - glucose) factor. |

### Resource Allocation Thresholds

| Threshold | Value | Used In | Justification |
|-----------|-------|---------|---------------|
| Minimum syntactic allocation | 0.30 | `embodied.py:41` | Floor for syntactic planning resources, maintaining minimal grammatical production capability. |
| High demand syntactic penalty | 0.70 | `embodied.py:42` | When demand > 5.0, syntactic resources reduced by 30%. Models resource competition under cognitive load. |
| Minimum attention allocation | 0.10 | `embodied.py:43` | Floor for attentional resources, preventing complete attention collapse. |
| Visual fatigue lexical penalty | 0.40 | `embodied.py:40` | Visual fatigue reduces lexical access by up to 40%. |
| Visual fatigue attention penalty | 0.50 | `embodied.py:43` | Visual fatigue reduces attention by up to 50%. |

### Syntactic Complexity Thresholds

| Threshold | Value | Used In | Justification |
|-----------|-------|---------|---------------|
| Syntactic collapse base | 4.0 | `causal_core.py:110` | Base syntactic depth threshold. Higher depths risk "syntactic_collapse" failure. |
| Syntactic collapse glucose factor | 3.5 | `causal_core.py:110` | Glucose extends syntactic capacity by up to 3.5 additional levels. |
| High syntactic demand | > 5.0 | `embodied.py:42` | Demand level triggering resource reallocation penalties. |
| Maximum syntactic demand | 10.0 | `embodied.py:105` | Upper bound for syntactic demand heuristic. |

---

## Cognitive State Phase Thresholds

Thresholds determining cognitive phase boundaries during simulated writing sessions.

| Threshold | Value | Used In | Justification |
|-----------|-------|---------|---------------|
| Peak phase end | minute <= 25 | `prompts.py:523` | First 25 minutes at maximum cognitive capacity. Based on attention span research. |
| Maintenance phase end | minute <= 50 | `prompts.py:525` | Minutes 26-50: sustained attention with periodic micro-lapses. |
| Fatigue phase end | minute <= 75 | `prompts.py:527` | Minutes 51-75: noticeable executive function degradation. |
| Deep Fatigue phase | minute > 75 | `prompts.py:529` | Minutes 76-90: severe resource depletion, formulaic output. |

### Cognitive Load Level Thresholds

| Threshold | Value | Used In | Justification |
|-----------|-------|---------|---------------|
| Low load threshold | combined > 0.75 | `prompts.py:325` | Full access to sophisticated vocabulary and syntax. |
| Moderate load threshold | combined > 0.50 | `prompts.py:327` | Occasional simplification of nested clauses. |
| High load threshold | combined > 0.25 | `prompts.py:329` | Marked preference for familiar constructions. |
| Severe load | combined <= 0.25 | `prompts.py:331` | Heavily formulaic output, minimal variation. |

### Latency Classification Thresholds

| Threshold | Value | Used In | Justification |
|-----------|-------|---------|---------------|
| Low latency | < 200 ms | `prompts.py:427` | Maintains full syntactic complexity. |
| Moderate latency | < 350 ms | `prompts.py:429` | Occasional pronoun distance effects acceptable. |
| High latency | < 500 ms | `prompts.py:431` | Increased reliance on proximal references. |
| Very high latency | >= 500 ms | `prompts.py:434` | Strong preference for simple reference chains. |

### Burst Speed Thresholds

| Threshold | Value | Used In | Justification |
|-----------|-------|---------|---------------|
| High burst speed | > 3.0 tokens/sec | `prompts.py:437` | May produce typos in rapid sequences. |
| Moderate burst speed | > 2.0 tokens/sec | `prompts.py:439` | Rare typos possible, immediately self-corrected. |
| Low burst speed | <= 2.0 tokens/sec | `prompts.py:442` | Careful production, minimal execution errors. |

### Glucose-Based Complexity Ceilings

| Threshold | Value | Used In | Justification |
|-----------|-------|---------|---------------|
| Full complexity glucose | > 0.70 | `prompts.py:445` | Permits full nested subordination, technical nominalization. |
| Moderate complexity glucose | > 0.50 | `prompts.py:447` | Max 2-level subordination, standard hedging. |
| Reduced complexity glucose | > 0.30 | `prompts.py:449` | Shallow embedding only, formulaic hedging. |
| Minimal complexity glucose | <= 0.30 | `prompts.py:452` | Minimal subordination, highly formulaic. |

---

## Sensory Intrusion Thresholds

Parameters for simulating environmental attention intrusions during writing sessions.

| Threshold | Value | Used In | Justification |
|-----------|-------|---------|---------------|
| Base intrusion probability | 0.10 | `prompts.py:224` | 10% intrusion chance at session start. |
| Maximum intrusion probability | 0.95 | `prompts.py:225` | Cap on intrusion probability. |
| Intrusion probability slope | 0.70 | `prompts.py:224` | Probability increases by 70% over 90-minute session. |
| Low severity end | minute <= 25 | `prompts.py:231` | Low severity intrusions in first 25 minutes. |
| Medium severity start | minute > 50 | `prompts.py:235` | Medium severity begins after 50 minutes. |
| High severity start | minute > 75 | `prompts.py:238` | High severity in final 15 minutes. |
| Context clarity threshold | >= 0.90 | `embodied.py:74` | Above 90% clarity, no context erosion applied. |
| Case erosion clarity | < 0.60 | `embodied.py:81` | Below 60% clarity, uppercase may erode to lowercase. |

---

## Injection Detection Thresholds

Thresholds for conceptual rupture detection and injection point selection.

| Threshold | Value | Used In | Justification |
|-----------|-------|---------|---------------|
| Rupture detection window | 50 words | `injection.py:34` | Sliding window size for lexical density analysis. |
| Lexical density shift | > 0.28 | `injection.py:78` | Shift in rare word density triggering rupture detection. |
| Transition cluster threshold | >= 1 | `injection.py:78` | Single discourse marker cluster sufficient for rupture. |
| Rare word length | > 8 chars | `injection.py:48-49` | Words longer than 8 characters considered "rare" for density calculation. |
| Minimum revision words | 50 words | `injection.py:100` | Revisions shorter than 50 words skipped for injection. |
| Edit probability per revision | 0.05 | `augment.py:303` | 5% base probability of span evolution per revision. |

---

## Boundary Erosion Thresholds

Boundary erosion measures how much injection span boundaries have shifted across subsequent revisions relative to the original span size. Higher erosion indicates greater integration with surrounding human text, supporting higher ambiguity classifications.

| Threshold | Value | Used In | Justification |
|-----------|-------|---------|---------------|
| MEDIUM ambiguity erosion | >= 0.10 | `annotations.py:421` | 10% boundary shift required for MEDIUM ambiguity. Indicates measurable boundary drift from surrounding human edits. |
| HIGH ambiguity erosion | >= 0.25 | `annotations.py:461` | 25% boundary shift required for HIGH ambiguity. Indicates substantial boundary integration making provenance harder to determine. |

Erosion is computed as the average total boundary shift (start + end) across all subsequent revisions, divided by the original span size. A value of 0.0 indicates no erosion; 1.0 indicates complete boundary shift equal to the original span size.

---

## Paranoia Level Thresholds

AI-detection awareness levels by academic field, affecting generation parameters.

| Threshold | Value | Used In | Description |
|-----------|-------|---------|-------------|
| Traditional humanities | 0.0 - 0.2 | `prompts.py:103` | Low tech awareness, minimal AI detection concern. |
| Social sciences | 0.2 - 0.4 | `prompts.py:104` | Moderate awareness. |
| Applied sciences/business | 0.4 - 0.6 | `prompts.py:105` | Notable awareness. |
| Computer science/data science | 0.6 - 0.8 | `prompts.py:106` | High awareness. |
| AI/ML/NLP specialists | 0.8 - 1.0 | `prompts.py:107` | Maximum awareness, strictest constraints. |

### Paranoia-Triggered Features

| Threshold | Value | Used In | Effect |
|-----------|-------|---------|--------|
| Natural variation trigger | > 0.50 | `prompts.py:593` | Adds natural variation constraint to naive prompts. |
| Lexical variation trigger | > 0.60 | `prompts.py:622` | Adds lexical variation constraint to topical prompts. |
| Authenticity requirements | > 0.70 | `prompts.py:658` | Adds full authenticity requirements to contextual prompts. |

---

## Trace and Validation Thresholds

| Threshold | Value | Used In | Justification |
|-----------|-------|---------|---------------|
| Minimum trace length (coupling) | > 10 | `causal_core.py:126` | Minimum trace events to compute resource coupling correlation. |
| Minimum trace length (metrics) | > 5 | `metrics.py:40`, `annotations.py:75` | Minimum trace events for general metrics computation. |
| Glucose increase tolerance | 0.0001 | `annotations.py:117` | Tolerance for glucose "increase" due to floating-point precision. Any increase above this triggers causal impossibility error. |

---

## References

1. **Repair Locality (1.0-3.5)**: Based on typing repair studies showing humans typically repair errors within 1-3 tokens of detection. See: Salthouse, T. A. (1984). Effects of age and skill in typing. *Journal of Experimental Psychology: General*.

2. **Resource Coupling (r > 0.6)**: Derived from cognitive resource competition models. Failure at time T should correlate with syntactic simplification at T+1 in human production.

3. **Glucose Depletion (0.9992)**: Calibrated to produce realistic fatigue curves matching self-reported cognitive fatigue in extended writing sessions (90 minutes).

4. **NCD Threshold (0.45)**: Empirically tuned on ScholaWrite revision patterns to balance detection precision and recall.

5. **Substantial Edit (0.20)**: Based on revision analysis where 20% token change typically indicates significant content rewriting rather than minor editorial corrections.

---

## Updating Thresholds

When modifying thresholds:

1. Update the constant value in the source file
2. Update this documentation with the new value and justification
3. Run the validation suite to ensure consistency
4. Consider backward compatibility for existing datasets

See `src/scholawrite/metrics.py` for centralized threshold constants.
