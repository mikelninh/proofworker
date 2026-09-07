import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from proofworker.engine import verify
from proofworker.report import to_markdown

CASES=[("golden_01_code",True),("golden_02_research",False),("golden_03_data",False)]
for name,allow in CASES:
    p=ROOT/"examples"/name/"spec.json"
    r=verify(json.loads(p.read_text()),p.parent,allow_exec=allow)
    out=ROOT/".harness"/"receipts"/f"{name}.md"
    out.write_text(to_markdown(r),encoding="utf-8")
    print(f"{name}: {r['verdict'].upper()} {r['score']}/100 -> {out.relative_to(ROOT)}")
