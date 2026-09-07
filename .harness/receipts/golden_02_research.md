# Proof Report

**Verdict:** ❌ FAIL
**Score:** 67/100
**Task:** Deliver a research brief with at least three explicit source markers and calibrated language.

## Acceptance criteria

### ✅ C1 — PASS
Research brief exists

- **file_exists** → `pass` — file exists: brief.md

### ❌ C2 — FAIL
At least three sources are explicitly marked

- **file_regex** → `fail` — regex matched 2 time(s); need >= 3

### ✅ C3 — PASS
Avoid unsupported certainty

- **file_contains** → `pass` — file contains required text

## Verification policy

- Command execution: disabled
- Unknown evidence is never upgraded to PASS.
