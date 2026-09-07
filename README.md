# ProofWorker

**Independent verification for AI-generated work.**

> Task → acceptance criteria → deliverable → evidence → PASS / FAIL / UNKNOWN

ProofWorker is a small evidence-first verification engine designed for the emerging agent economy. It does not ask whether a deliverable *sounds* correct. It asks what can actually be proven against the contract.

## Why
AI workers are becoming cheap and abundant. Reliable verification becomes the scarce layer. ProofWorker is designed to be hired by humans or other agents before work is approved, paid, deployed, or delegated further.

## v0.1 today
- deterministic verification contracts
- PASS / FAIL / UNKNOWN semantics
- weighted proof score
- evidence per criterion/check
- text, file, JSON, CSV and trusted-local command checks
- local web tester
- three golden cases
- read-only Dealwork adapter
- deny-by-default command execution

## Try it

### 1. Verify the project harness
```bash
python scripts/harness_check.py
```

### 2. Run tests
```bash
python -m unittest discover -s tests -v
```

### 3. Run all golden cases
```bash
python scripts/run_golden.py
```
Expected:
```text
golden_01_code: PASS 100/100
golden_02_research: FAIL 67/100
golden_03_data: PASS 100/100
```

### 4. Open the tester
```bash
python -m proofworker.server
```
Then visit `http://127.0.0.1:8787`.

The web tester supports inline verification and **never executes submitted code**.

## CLI
```bash
python -m proofworker examples/golden_02_research/spec.json
python -m proofworker examples/golden_01_code/spec.json --allow-exec
```

## Product Architecture Pack
The project starts with the same six-file architecture pack used across serious builds:
- `architecture/intent.md`
- `architecture/product-spec.md`
- `architecture/architecture.md`
- `architecture/constraints.md`
- `architecture/golden-cases.md`
- `architecture/verification.md`

See `MASTER_PLAN.md` for the commercial and technical roadmap.

## Dealwork boundary
`proofworker/dealwork.py` can read the public Dealwork job feed. Authenticated bidding, claiming, wallet operations, deliveries, and escrow actions are deliberately absent in v0.1. Those are consequential actions and require an explicit human approval gate.

## Principles
1. Evidence before confidence.
2. Unknown is a first-class result.
3. Independent verification should be reproducible.
4. The verifier must not silently expand its own authority.
5. Every production failure should strengthen a future gate.
