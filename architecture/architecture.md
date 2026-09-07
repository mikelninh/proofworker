# Architecture

## System shape

`Verification Contract → Check Planner / Adapter → Deterministic Check Engine → Evidence Bundle → Criterion Verdicts → Proof Report`

## Components
- `proofworker/engine.py` — deterministic evaluation and evidence capture
- `proofworker/report.py` — human-readable proof report
- `proofworker/cli.py` — local verification interface
- `proofworker/server.py` — zero-dependency local web tester
- `proofworker/dealwork.py` — public/read-only marketplace adapter
- `web/` — quiet editorial tester UI
- `examples/` — three golden cases
- `.harness/` — durable project/task state and receipts

## Authority boundary
Models may later propose checks or interpret ambiguous language. They must not self-authorize a PASS. PASS comes only from checks whose evidence policy is known.

## Execution boundary
Untrusted code execution is disabled. Trusted local fixtures may use bounded command checks only with explicit `--allow-exec`. Production code verification requires an isolated sandbox in a later phase.

## External actions
Marketplace reads are A0. Drafting a bid is A1. Creating a bid/claim, submitting a deliverable, spending funds, or approving escrow is A3 and requires a human approval gate until explicitly promoted.
