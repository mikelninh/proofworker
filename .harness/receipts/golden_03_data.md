# Proof Report

**Verdict:** ✅ PASS
**Score:** 100/100
**Task:** Deliver a cleaned CSV with unique IDs, exactly three output rows, and a reconciliation log.

## Acceptance criteria

### ✅ C1 — PASS
Output has exactly three records

- **csv_row_count** → `pass` — row count 3; expected 3

### ✅ C2 — PASS
IDs are unique

- **csv_unique** → `pass` — 0 duplicate value(s) in id

### ✅ C3 — PASS
Change log reconciles output rows

- **json_equals** → `pass` — JSON value matches expected

## Verification policy

- Command execution: disabled
- Unknown evidence is never upgraded to PASS.
