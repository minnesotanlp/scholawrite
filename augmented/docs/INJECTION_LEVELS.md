# Injection Levels

## 1) Overview

Injection levels define the **sophistication of externally inserted content** relative to the target document's context. They form one axis of the annotation schema, orthogonal to trajectory states and ambiguity flags.

The three levels represent increasing difficulty for process-integrity methods to detect the insertion based on content coherence alone.

## 2) Level Definitions

### 2.1 Naive

**Topic-agnostic or loosely related insertions.**

Properties:
- Content may be from a different domain or topic entirely.
- No attempt to match the discourse context of the insertion point.
- Stylistic and terminological mismatch is common.
- Represents the easiest case for discontinuity detection.

Example: inserting a paragraph about climate policy into a computer science methods section.

Generator requirements:
- May use generic prompts without document context.
- No access to surrounding text is required.

### 2.2 Topical

**Same-domain but context-agnostic insertions.**

Properties:
- Content is from the same broad domain as the target document.
- Terminology and topic area are appropriate.
- No awareness of the specific discourse structure, argument flow, or local context.
- May exhibit local coherence gaps (non-sequiturs within the section).

Example: inserting a well-written paragraph about neural network architectures into a paper on NLP, but at a point where the paper is discussing evaluation metrics.

Generator requirements:
- Prompt includes domain/topic information.
- No access to the specific surrounding sentences or section context.

### 2.3 Contextual

**Locally coherent insertions aligned to nearby discourse.**

Properties:
- Content is coherent with the immediately surrounding text.
- Matches the argument flow and section purpose.
- Stylistic alignment with the document is attempted.
- Represents the hardest case for content-based detection.
- Process-level signals (revision dynamics) become the primary detection avenue.

Example: inserting a paragraph that logically follows the previous paragraph and leads into the next, using consistent terminology and argumentation style.

Generator requirements:
- Prompt includes surrounding context (preceding and following sentences/paragraphs).
- Document-level metadata (section title, abstract) may be provided.
- Higher-capability generators are typically required.

## 3) Level Comparison

| Property | Naive | Topical | Contextual |
|----------|-------|---------|------------|
| Domain match | No | Yes | Yes |
| Topic match | No/Loose | Yes | Yes |
| Local coherence | No | Partial | Yes |
| Style match | No | Partial | Attempted |
| Detection difficulty (content) | Low | Medium | High |
| Detection difficulty (process) | Uniform | Uniform | Uniform |
| Generator context needed | None | Domain only | Full local context |

## 4) Relationship to Generator Classes

Generator classes (weak/mid/strong) are **distinct from** injection levels:

- **Generator class** describes the capability of the text generation system.
- **Injection level** describes the information available to the generator at insertion time.

A strong generator with no context produces a **naive** injection. A weak generator with full context may produce a **contextual** injection (though quality may vary).

The combination is recorded in annotation metadata:
- `injection_level`: naive / topical / contextual
- `generator_class`: weak / mid / strong
- `prompt_hash`: identifies the specific prompt template used

## 5) Prompt Templates

Each injection level uses distinct prompt template families (defined in `src/scholawrite/prompts.py`):

- **Naive**: `generate_text(topic=random_topic)` — no document context.
- **Topical**: `generate_text(domain=doc_domain, topic=doc_topic)` — domain-matched.
- **Contextual**: `generate_text(preceding=..., following=..., section=..., abstract=...)` — full local context.

All prompts are hashed and recorded for reproducibility.

## 6) Distribution Goals

The augmented dataset targets a balanced distribution across levels:
- Approximately equal representation of naive, topical, and contextual injections.
- Each level is combined with all trajectory states (cold/warm/assimilated).
- The full matrix (3 levels x 3 trajectories = 9 cells) is populated.

Actual counts are recorded in `data/augmented/stats.json` under `stats.labels`.

## 7) Implementation Reference

Injection level enum is defined in `src/scholawrite/schema.py`:
- `InjectionLevel` enum: `NAIVE`, `TOPICAL`, `CONTEXTUAL`
- `Label` enum includes injection labels: `INJECTION_NAIVE`, `INJECTION_TOPICAL`, `INJECTION_CONTEXTUAL`

Injection generation logic is implemented in `src/scholawrite/injection.py` and `src/scholawrite/generators.py`.

## 8) Validation

- Labels must use the `injection.*` namespace: `injection.naive`, `injection.topical`, `injection.contextual`.
- Labels are validated against `docs/LABEL_TAXONOMY.md` by `scripts/lint_data.py`.
- Each injection record must include `injection_level` as a required field.
- `tests/test_injection.py` verifies that generated injections conform to their declared level.

## 9) Relationship to Baselines

Baseline methods (`src/scholawrite/baselines.py`) are evaluated per-level:
- **Lexical shift**: expected to perform well on naive, poorly on contextual.
- **Semantic discontinuity**: expected to perform well on naive/topical, variably on contextual.
- **Change-point detection**: process-level signal, expected to be level-independent.

Results are disaggregated by level in `results/baselines/` outputs.
