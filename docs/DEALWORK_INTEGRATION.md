# Dealwork Integration Plan

## Verified current platform shape (2026-09-07)
Dealwork exposes `/api/v1/jobs`, HMAC-authenticated agent endpoints, contracts/deliverables, and supports agent-to-agent hiring. Their own product documentation explicitly gives the example of a coding agent hiring QA to check its work.

## v0.1
Read public jobs only. No key required. No marketplace mutation.

## v0.2 connection flow
1. Generate/connect token through Dealwork's agent connection flow.
2. Human authorizes ownership in browser.
3. Store agent secret outside git.
4. Implement HMAC signer.
5. Read `/agents/me` and matching jobs.
6. Draft candidate actions.
7. Human approves any bid/claim/delivery/spend action.
8. Capture contract + proof + payout/cost receipt.

## Initial service listing hypothesis
**Independent AI Deliverable Verification**

Buyer supplies task, acceptance criteria, and deliverable. ProofWorker returns criterion-level PASS/FAIL/UNKNOWN with reproducible evidence.

Start with deterministic text/data checks; code verification is limited to safe/sandboxed execution when that runner exists.
