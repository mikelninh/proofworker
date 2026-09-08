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

It may not claim jobs, spend funds, submit contract deliverables, approve/release escrow, or execute untrusted remote code.

## v0.2b bounded revenue operator
`scripts/revenue_operator.py` extends the market test from passive discovery to a human-gated revenue loop.

It may automatically:
- scan the curated and microtask Dealwork job feeds
- fetch public job detail and public bid-distribution information
- distinguish likely buyer tasks from provider self-promotion/noise
- apply transparent fit, effort, competition and risk heuristics
- hard-block obviously unsafe security-sensitive work
- create local market-scan receipts with no credentials
- prepare price and proposal drafts for qualified opportunities
- read the owner's bids, contracts, pending listing requests and earnings

It may submit a Dealwork bid only when all of these are true:
1. the opportunity clears the current `QUALIFY` gate;
2. no blocked risk flag is present;
3. the current Dealwork OpenAPI `CreateBid` request schema can be mapped without guessing any required field;
4. the owner explicitly enables execution; and
5. the owner types the exact per-job confirmation token immediately before submission.

It may not:
- submit bids unattended
- claim jobs
- accept paid contracts automatically
- spend or transfer wallet funds
- submit paid deliverables
- release/approve escrow
- run unknown third-party code without the approved sandbox

## Acceptance criteria for v0.2 market/revenue test
1. `scripts/dealwork_connect.py` and `scripts/revenue_operator.py` compile without network access.
2. Revenue-operator self-tests prove a clear buyer task qualifies, provider-style marketplace noise is skipped, and security-sensitive work is skipped.
3. Credentials are never printed, committed, or written inside the repository.
4. Owner authorization precedes agent onboarding.
5. Listing publication requires an explicit human action.
6. Market scans include evidence-friendly local receipts and clearly label EV/win estimates as heuristics.
7. A bid cannot be submitted without a per-job human confirmation token.
8. A changed/unknown Dealwork bid schema fails closed instead of guessing required fields.
9. First accepted work, first earned revenue and first cash received are recorded separately before autonomy expands.

## Commercial hypothesis
Buyers and agents will pay a small fixed fee for independent verification when the cost of a wrong approval exceeds the verification fee.

## Pricing experiment
Launch listing:
- Standard evidence-backed proof: **$5**

Early outbound bid strategy:
- prefer small, clear $5–$50 tasks until three clean paid wins
- modest early-reputation discount only; do not race to the bottom
- use a conservative 10% fee assumption for EV ranking even when a lower AI-to-AI fee may apply

If demand appears, test a ladder rather than assuming it:
- Smoke proof: $3
- Standard proof: $9
- Deep proof: $25

Pricing remains a hypothesis until a real buyer pays.
