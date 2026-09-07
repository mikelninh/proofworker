from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import verify
from .report import to_markdown


def main() -> None:
    p = argparse.ArgumentParser(prog="proofworker")
    p.add_argument("spec", help="Path to verification spec JSON")
    p.add_argument("--allow-exec", action="store_true", help="Allow command checks for trusted local fixtures")
    p.add_argument("--json", action="store_true", help="Print JSON instead of Markdown")
    args = p.parse_args()

    path = Path(args.spec).resolve()
    spec = json.loads(path.read_text(encoding="utf-8"))
    report = verify(spec, base_dir=path.parent, allow_exec=args.allow_exec)
    print(json.dumps(report, indent=2) if args.json else to_markdown(report))


if __name__ == "__main__":
    main()
