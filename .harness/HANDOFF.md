# Handoff

## Status
ProofWorker v0.1 bootstrap is complete and the verified source is now in `mikelninh/proofworker`.

## Evidence
- Harness: PASS — 13 required files, durable JSON state parses.
- Unit tests: PASS — 6/6.
- GC-01 code: PASS 100/100.
- GC-02 research: FAIL 67/100, exactly as designed.
- GC-03 data: PASS 100/100.
- Local web/API smoke: PASS 100/100.
- Attempted web `command` check: blocked with HTTP 400.
- GitHub repository: created and populated with the Product Architecture Pack, harness, engine, tests, golden cases, UI and CI workflow.

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
- GitHub CI must be observed on the remote commit before v0.1 is considered remotely verified.

## Exact next action
Observe remote CI. If green, connect ProofWorker to Dealwork under the A3 human-approval boundary and run the first live market test without autonomous bidding, claiming, spending or delivery.
