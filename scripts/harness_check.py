import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
required=[
 "README.md","AGENTS.md","MASTER_PLAN.md",
 "architecture/intent.md","architecture/product-spec.md","architecture/architecture.md",
 "architecture/constraints.md","architecture/golden-cases.md","architecture/verification.md",
 ".harness/project.json",".harness/active-task.json",".harness/roadmap.json",".harness/HANDOFF.md"
]
missing=[p for p in required if not (ROOT/p).exists()]
if missing: raise SystemExit("Missing: "+", ".join(missing))
for p in [".harness/project.json",".harness/active-task.json",".harness/roadmap.json"]:
    json.loads((ROOT/p).read_text())
print(f"Harness OK: {len(required)} required files present; JSON state parses.")
