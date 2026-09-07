# Threat Model — v0.1

## Assets
- host machine
- marketplace credentials/wallet
- customer artifacts
- verifier integrity
- proof receipts

## Primary threats
1. malicious submitted code attempts host escape
2. path traversal reads unrelated files
3. prompt or deliverable text tries to redefine acceptance criteria
4. unsupported evidence is presented as proof
5. marketplace credentials leak into repo/logs
6. autonomous agent bids/spends/delivers outside owner intent
7. verifier implementation and worker implementation collude or share the same failure

## v0.1 controls
- web mode: no command execution
- command checks require explicit local `--allow-exec`
- argv arrays only; 30s hard cap
- path resolution constrained to workspace root
- acceptance criteria are data, not instructions embedded inside deliverables
- UNKNOWN is conservative default on blocked/error/unsupported evidence
- Dealwork adapter has no authenticated mutation methods
- secrets excluded from repository

## Required before remote-code launch
Ephemeral sandbox, network policy, resource quotas, dependency policy, filesystem isolation, artifact limits, malicious fixture suite, and independent security review of the runner boundary.
