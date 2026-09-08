# Constraints

## Product truth
- Unknown evidence must remain `UNKNOWN`.
- A polished deliverable is not proof of correctness.
- Synthetic golden-case evidence is not customer evidence.
- ProofWorker must distinguish verification evidence from certification or professional assurance.
- Opportunity scores and estimated win probabilities are prioritization heuristics, not guarantees.
- A posted listing, submitted bid, accepted bid, earned revenue and cash received are separate states and must never be conflated.

## Security
- No secrets in repository state, examples, logs, or receipts.
- Marketplace credentials must stay on the owner's local machine or a proper secret store; never commit or print API keys/HMAC secrets.
- No arbitrary shell strings; trusted command checks use argv arrays.
- Command execution is disabled by default and capped at 30 seconds.
- Workspace paths must not escape their verification root.
- Web mode never executes submitted commands.
- Remote repository execution requires sandboxing before launch.
- Security-sensitive tasks that imply credential theft, phishing, malware, auth bypass, exfiltration or attacks against live targets are excluded from the revenue loop.

## Autonomy
- A0 read/search/analyse: automatic.
- A1 local reversible draft/test: automatic.
- A2 branch/PR/preview: logged, normally automatic.
- A3 bid/claim/deliver/spend/publish/deploy: human approval required.
- A4 destructive/sensitive/high-impact: explicit approval + independent verification.
- Dealwork owner connection requires browser authorization.
- Dealwork listing publication requires an explicit human action; no background auto-listing.
- The revenue operator may prepare bids automatically but may submit a bid only after an exact per-job human confirmation token.
- No unattended bids, claims, wallet actions, contract acceptance, deliverable submissions or escrow events.
- Claims, spending, contract delivery and escrow mutations remain unimplemented in the revenue operator.

## Marketplace
Dealwork is a distribution adapter. The core verification engine must not depend on Dealwork-specific state.

The revenue loop must prefer real buyer demand over provider self-promotion, clearly scoped work over ambiguous work, and small verifiable tasks over high-complexity hero bets until three clean paid wins exist.

## Design
The UI should communicate task → criteria → evidence → verdict within seconds. Prefer quiet/editorial clarity over dashboard clutter.
