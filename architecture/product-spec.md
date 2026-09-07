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
6. Dealwork adapter is read-only.
7. Architecture pack and durable harness are present and truthful.

## Commercial hypothesis
Buyers and agents will pay a small fixed fee for independent verification when the cost of a wrong approval exceeds the verification fee.

## Candidate pricing experiment
- Smoke proof: $3
- Standard proof: $9
- Deep proof: $25
Pricing is a hypothesis, not yet validated.
