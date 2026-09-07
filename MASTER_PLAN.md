# ProofWorker Master Plan

## North star
Build the trust layer for the agent economy: independent, reproducible verification of AI-generated work before approval, payment, deployment, or delegation.

## Thesis
AI supply is becoming cheap. Trust in outputs becomes the scarce layer. The opportunity is not another general-purpose worker; it is infrastructure that can answer **"does this actually satisfy the contract?"** and show the evidence.

## Wedge
Start on Dealwork because the marketplace already supports human↔AI and AI↔AI contracts, explicit acceptance criteria, escrow, and agent-to-agent QA patterns. The product remains marketplace-agnostic.

## v0.1 — today: prove the proof
**Goal:** a working end-to-end verifier we can test immediately.

Ship:
- Product Architecture Pack + agent harness
- deterministic verification contract schema
- PASS / FAIL / UNKNOWN engine
- Markdown + JSON Proof Reports
- three golden cases
- local browser tester
- read-only Dealwork jobs adapter
- deny-by-default execution/security boundaries

Success:
- GC-01 PASS 100
- GC-02 FAIL
- GC-03 PASS 100
- all unit/harness checks green
- browser API returns a proof report

## v0.2 — Dealwork market test
**Goal:** validate willingness to pay without autonomous financial risk.

1. Connect ProofWorker as an owned Dealwork agent.
2. Read matching jobs and identify verification demand.
3. Publish one sharply scoped service: **Independent AI Deliverable Verification**.
4. Start with one category where evidence can be deterministic.
5. Human approves every bid, claim, delivery, and spend.
6. Save contract outcome, proof result, revisions, compute cost, payout, and margin.

Candidate offer:
- $3 Smoke Proof — simple deterministic acceptance checks
- $9 Standard Proof — multi-criterion evidence report
- $25 Deep Proof — repository/data/research bundle with stronger verification

## v0.3 — Code Proof sandbox
**Goal:** safely verify third-party repositories.

Add:
- ephemeral isolated runner
- network-off by default
- CPU/memory/time quotas
- dependency install policy
- test discovery
- build verification
- artifact hashes
- reproducible receipt

Promotion gate: adversarial fixture suite proves the sandbox cannot escape its boundary.

## v0.4 — Research Proof
Add source retrieval, claim→source mapping, quote/URL validation, publication-date checks, and unsupported-claim detection. LLMs may propose mappings; deterministic/source-grounded evidence controls verdicts.

## v0.5 — Data Proof
Add input/output reconciliation, schema conformance, duplicate/null rules, statistical invariants, transform logs, and row-level sampling evidence.

## v0.6 — ProofWorker API
Expose verification as an API so other agents can call ProofWorker before they submit work or release escrow.

Commercial direction:
- per-proof pricing
- prepaid agent credits
- marketplace integrations
- team/enterprise verification policies

## v1 — autonomous QA worker, bounded
ProofWorker may automatically accept only whitelisted verification jobs within explicit spend, execution, category, confidence, and concurrency limits. Consequential marketplace actions remain policy-controlled and auditable.

## v2 — DealForge
Once ProofWorker itself is reliable, build the higher-level micro-agency orchestrator:
`find work → estimate EV → execute/delegate → ProofWorker verifies → human/policy gate → deliver → learn from outcome`.

## Core metrics
### Quality
- false PASS rate: target 0 on golden/adversarial suite
- reproducibility rate
- UNKNOWN calibration
- customer revision rate

### Economics
- payout / proof
- compute + subcontract cost / proof
- gross margin
- win rate
- approval rate
- time-to-cash

### Trust
- evidence completeness
- verifier disagreement rate
- dispute rate
- repeat buyers / calling agents

## Kill criteria
Do not keep polishing if, after a reasonable live sample:
- buyers will not pay more than verification cost,
- deterministic criteria are too rare to create value,
- false PASS cannot be held near zero,
- marketplace demand is structurally too small.

In that case, keep the engine and move distribution to CI, agent frameworks, procurement, or enterprise workflow approvals.

## Today’s exact next boundary
The repo can be tested locally now. The next external action is **connecting the owned Dealwork agent**, which requires browser authorization and becomes the first explicit human-controlled promotion step.
