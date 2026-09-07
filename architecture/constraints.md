# Constraints

## Product truth
- Unknown evidence must remain `UNKNOWN`.
- A polished deliverable is not proof of correctness.
- Synthetic golden-case evidence is not customer evidence.
- ProofWorker must distinguish verification evidence from certification or professional assurance.

## Security
- No secrets in repository state, examples, logs, or receipts.
- No arbitrary shell strings; trusted command checks use argv arrays.
- Command execution is disabled by default and capped at 30 seconds.
- Workspace paths must not escape their verification root.
- Web mode never executes submitted commands.
- Remote repository execution requires sandboxing before launch.

## Autonomy
- A0 read/search/analyse: automatic.
- A1 local reversible draft/test: automatic.
- A2 branch/PR/preview: logged, normally automatic.
- A3 bid/claim/deliver/spend/publish/deploy: human approval required.
- A4 destructive/sensitive/high-impact: explicit approval + independent verification.

## Marketplace
Dealwork is a distribution adapter. The core verification engine must not depend on Dealwork-specific state.

## Design
The UI should communicate task → criteria → evidence → verdict within seconds. Prefer quiet/editorial clarity over dashboard clutter.
