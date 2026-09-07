# Verification

## Required local gates
```bash
python scripts/harness_check.py
python -m unittest discover -s tests -v
python scripts/run_golden.py
```

## v0.1 evidence rules
- A check records what it tested and the observed result.
- Criterion PASS requires every required check to PASS.
- Any failed required check makes the criterion FAIL.
- Unsupported, blocked, missing, or errored evidence yields UNKNOWN unless another required check already proves failure.
- UNKNOWN contributes zero toward the score.
- Overall FAIL takes precedence over UNKNOWN; UNKNOWN takes precedence over PASS.

## Release gate
Before promotion:
1. harness valid
2. unit tests green
3. golden receipts generated
4. no secrets committed
5. README matches current behavior
6. Dealwork consequential actions remain gated

## Watch plan
Track:
- false PASS rate — highest-severity metric
- UNKNOWN rate
- verifier execution failures
- cost per proof
- time per proof
- customer revision/dispute rate
- revenue and gross margin per verification category
