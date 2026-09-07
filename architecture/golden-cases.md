# Golden Cases

## GC-01 — Code / expected PASS
**Task:** deliver a Python greeting function with an automated test.

**Proof:** implementation exists, test exists, trusted local test suite exits 0.

**Expected:** `PASS`, 100/100.

**Why it matters:** demonstrates that ProofWorker can verify executable evidence instead of trusting a developer's statement.

## GC-02 — Research / expected FAIL
**Task:** deliver a research brief with at least three explicit source markers and calibrated language.

**Fixture:** brief has only two source markers but uses appropriately calibrated language.

**Expected:** `FAIL`.

**Why it matters:** a plausible-looking brief should still fail a measurable contract requirement.

## GC-03 — Data / expected PASS
**Task:** deliver cleaned CSV with exactly three output rows, unique IDs, and reconciliation log.

**Proof:** CSV parser checks row count and uniqueness; JSON log reconciles row count.

**Expected:** `PASS`, 100/100.

## Promotion rule
A new verifier capability does not ship until at least one golden case proves its happy path and one adversarial or failure case proves it can reject bad evidence.
