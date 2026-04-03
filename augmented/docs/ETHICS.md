# Ethical Considerations

## 1) Framing: Process Integrity, Not Surveillance

ScholaWrite-Augmented is designed to study **process integrity** in revision-tracked scholarly writing. It does **not** provide tools for authorship attribution, AI detection, or enforcement of writing norms.

The project explicitly separates:
- **Assistive use** (process-consistent, iteratively integrated) from
- **Opaque external insertion** (process-inconsistent, lacking revision integration)

This framing avoids stigmatizing legitimate tool use while enabling research into revision-trace discontinuities.

## 2) Intended Use

- Academic research on process integrity and revision dynamics.
- Benchmarking methods for surfacing process discontinuities.
- Studying boundary erosion and ambiguity in collaborative/assisted writing.
- Informing policy through evidence rather than enforcement.

## 3) Non-Use / Misuse Risks

This dataset MUST NOT be used for:
- **Punitive enforcement**: automated decisions about academic misconduct, hiring, or credentialing.
- **Sole authorship determination**: the dataset cannot support claims of cognitive origin.
- **Surveillance**: monitoring writers without consent or due process.
- **High-stakes decisions**: without human review and contextual judgment.
- **Reverse identification**: of authors, papers, institutions, or projects in the seed data.
- **Stigmatization**: framing all external tool use as misconduct.

## 4) Bias and Limitations

- **Generator bias**: synthetic insertions inherit biases from the models that produced them. Downstream users must account for this when interpreting results.
- **English-only**: the seed dataset and augmentations are in English, limiting generalizability.
- **Academic domain**: findings may not transfer to other writing contexts (journalism, creative writing, technical documentation).
- **Temporal snapshot**: generator capabilities evolve; results may not hold for future models.

## 5) Dual-Use Awareness

The same techniques that surface process discontinuities could, in theory, be used to:
- Train better evasion strategies for opaque insertion.
- Develop overly aggressive detection tools that produce false accusations.

Mitigations:
- The dataset is positioned as a **research benchmark**, not a deployable detection system.
- All documentation emphasizes graded evidence over binary classification.
- The terminology contract (`docs/TERMINOLOGY.md`) prohibits framing as "AI detection."
- Non-use language is included in all release artifacts.

## 6) Privacy and Safety

- No personally identifying information is introduced by generation.
- PII scans are mandatory prior to release (see `docs/PROTOCOL.md` Section 11).
- The seed dataset terms prohibit reverse identification; this constraint is inherited.
- See `docs/ATTRIBUTION_AND_LICENSE.md` for binding terms.

## 7) Harm Evaluation

The baselines and harm analysis (`src/scholawrite/harm.py`, `scripts/run_harm.py`) explicitly measure:
- False-positive rates disaggregated by relevant subgroups.
- Potential for disparate impact if methods were deployed.
- The gap between evidence and determination.

Results are reported in `results/harm/` and discussed in the paper with appropriate caveats.

## 8) Responsible Disclosure

If this dataset or associated methods are found to cause unanticipated harm:
- Report to the maintainers via the [GitHub issue tracker](https://github.com/writerslogic/scholawrite-augmented/issues).
- Do not deploy findings as enforcement tools without independent ethical review.

## 9) Relationship to Prior Work

This project differs from prior "AI detection" datasets in that it:
- Does not claim to distinguish human from machine text.
- Models process-level events rather than text-level features.
- Explicitly accounts for ambiguity and boundary erosion.
- Positions assistance as compatible with process integrity.

## 10) Terminology Binding

All ethical claims and framing in this document are bound by `docs/TERMINOLOGY.md`. Terms prohibited by that contract are prohibited here.
