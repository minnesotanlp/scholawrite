<!-- Purpose: tests/fixtures/README.md -->
# Test Fixtures

Small, deterministic fixtures for unit tests.

- Keep fixtures minimal and human-readable.
- Store any JSONL fixtures in this folder.

## Golden Files

Golden files ensure serialization/deserialization determinism.

| File | Purpose | Tests |
|------|---------|-------|
| `seed_document_golden.jsonl` | SeedDocument roundtrip verification | `TestGoldenFileSeedDocuments` |
| `augmented_document_golden.jsonl` | AugmentedDocument with enum validation | `TestGoldenFileAugmentedDocuments` |
| `pii_sample.jsonl` | PII detection test cases | `test_pii.py` |

## Updating Golden Files

Golden files should only be updated when:
1. Schema changes are intentional and documented
2. The change is verified to be correct
3. All dependent tests pass with the new golden file
