# Handoff

## Status
ProofWorker v0.1 is remotely verified. The verified product source is in `mikelninh/proofworker` on commit `3ce9b1764236e2e32e019bc73c58914717d6012f`.

## Evidence
- Harness: PASS — 13 required files, durable JSON state parses.
- Unit tests: PASS — 6/6.
- GC-01 code: PASS 100/100.
- GC-02 research: FAIL 67/100, exactly as designed.
- GC-03 data: PASS 100/100.
- Local web/API smoke: PASS 100/100.
- Attempted web `command` check: blocked with HTTP 400.
- GitHub repository: populated with Product Architecture Pack, harness, engine, tests, golden cases, UI and CI workflow.
- Remote GitHub Actions `verify` run `34145659628`: SUCCESS on product commit `3ce9b1764236e2e32e019bc73c58914717d6012f`.

## Decisions
- Core stays marketplace-agnostic.
- Dealwork is read-only in v0.1.
- Unknown evidence never becomes PASS.
- Public/web verification cannot execute submitted commands or inspect arbitrary workspace files.
- Trusted local fixtures may execute bounded argv commands only with explicit `--allow-exec`.

## Open risks
- No live Dealwork agent is connected yet; connection requires owner authorization in the browser.
- Customer repository execution still needs an isolated sandbox.
- Pricing remains a hypothesis until the first live market test.

## Exact next action
Start v0.2: connect ProofWorker to Dealwork under the A3 human-approval boundary, inspect live verification-fit jobs, publish/test the verification offer, and run the first market test without autonomous bidding, claiming, spending or delivery.
