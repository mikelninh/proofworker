# AGENTS.md — ProofWorker

## Mission
Build an evidence-first verification layer for AI-generated work. Never confuse confidence, polish, or model self-report with proof.

## Start here
1. Read `README.md`.
2. Read `.harness/project.json`.
3. Read `.harness/active-task.json` and `.harness/HANDOFF.md`.
4. Read the six files in `architecture/` relevant to the task.

## Contract before work
Every substantial task defines goal, sources, outputs, constraints, done criteria, forbidden actions, risk class, retry budget, and next owner.

## Roles
- Chief — scopes/routes; does not self-verify consequential work.
- Builder — implements checks, adapters, UI, or infra.
- Verifier — independently checks tests, evidence, and claims.
- Operator — performs approved external actions after gates.

## Action classes
- A0 Observe — automatic.
- A1 Local reversible — automatic.
- A2 Shared reversible — logged, normally automatic.
- A3 Consequential external action — human approval required.
- A4 High-impact/sensitive/destructive — explicit approval + stronger independent verification.

## Verification
Minimum gates:
```bash
python scripts/harness_check.py
python -m unittest discover -s tests -v
python scripts/run_golden.py
```
Never say a command passed unless it ran and its evidence was captured.

## Durable state
Chat is not the system of record. Keep current state in `.harness/`, accepted evidence in `.harness/receipts/`, and keep the six-file architecture pack truthful when product behavior changes.

## Hard boundaries
- Unknown is not PASS.
- Models may interpret; evidence policy controls authority.
- No secrets in repo state.
- No arbitrary untrusted code execution.
- Dealwork bid/claim/deliver/spend actions are A3 until explicitly promoted.
- ProofWorker provides verification evidence, not legal/security certification.

## Failure upgrades
A repeated failure must become a stronger test, check, boundary, fixture, or harness rule so it is less likely to recur.
