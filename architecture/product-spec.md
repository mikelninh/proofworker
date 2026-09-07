# Product Spec

## v0.1 input
A verification contract contains:
- task description
- one or more acceptance criteria
- criterion weights
- checks that can produce evidence
- optional deliverable text and/or trusted local workspace

## v0.1 output
A Proof Report contains:
- overall verdict: `pass | fail | unknown`
- score from 0–100
- per-criterion verdict
- check-level evidence and summaries
- execution policy used

## Supported checks
- inline text contains / forbids / regex
- file existence / content / regex
- JSON equality
- CSV row count and uniqueness
- trusted-local command exit verification

## Acceptance criteria for v0.1
1. Three golden cases run deterministically with expected verdicts.
2. Web tester can run inline verification without executing submitted code.
3. CLI can produce Markdown or JSON reports.
4. Path traversal is blocked.
5. Command execution is deny-by-default.
6. Core Dealwork adapter remains read-only.
7. Architecture pack and durable harness are present and truthful.

## v0.2 market-test adapter
The optional owner-first Dealwork connector may:
- create a temporary owner-authorization link
- open the authorization URL in the user's browser
- register ProofWorker only after Dealwork reports owner authorization
- save returned agent credentials locally outside the repository
- publish one fixed-price launch listing only after explicit human confirmation
- read the public job feed and rank verification-fit opportunities

It may not bid, claim, spend, submit contract deliverables, approve/release escrow, or execute untrusted remote code.

## Acceptance criteria for v0.2 market test
1. `scripts/dealwork_connect.py` compiles without network access.
2. Credentials are never printed, committed, or written inside the repository.
3. Owner authorization precedes agent onboarding.
4. Listing publication requires an explicit CLI flag and human confirmation unless the human additionally passes `--yes`.
5. Market scanning is read-only.
6. No bid/claim/wallet/contract mutation endpoints are implemented.
7. First live listing outcome and economics are recorded as evidence before pricing or autonomy expands.

## Commercial hypothesis
Buyers and agents will pay a small fixed fee for independent verification when the cost of a wrong approval exceeds the verification fee.

## Pricing experiment
Launch test:
- Standard evidence-backed proof: **$5**

If demand appears, test a ladder rather than assuming it:
- Smoke proof: $3
- Standard proof: $9
- Deep proof: $25

Pricing remains a hypothesis until a real buyer pays.
