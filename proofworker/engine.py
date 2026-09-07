from __future__ import annotations

import csv
import json
import re
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


@dataclass
class CheckResult:
    type: str
    status: str
    summary: str
    evidence: dict[str, Any]


@dataclass
class CriterionResult:
    id: str
    text: str
    status: str
    weight: float
    checks: list[CheckResult]


class VerificationError(Exception):
    pass


def _resolve(workspace: Path, rel: str) -> Path:
    p = (workspace / rel).resolve()
    root = workspace.resolve()
    if root != p and root not in p.parents:
        raise VerificationError(f"Path escapes workspace: {rel}")
    return p


def _run_check(check: dict[str, Any], spec: dict[str, Any], workspace: Path, allow_exec: bool) -> CheckResult:
    ctype = check.get("type", "")
    deliverable = str(spec.get("deliverable", ""))

    try:
        if ctype == "text_contains":
            value = str(check.get("value", ""))
            ok = value in deliverable
            return CheckResult(ctype, "pass" if ok else "fail", f"deliverable {'contains' if ok else 'does not contain'} required text", {"value": value})

        if ctype == "text_not_contains":
            value = str(check.get("value", ""))
            ok = value not in deliverable
            return CheckResult(ctype, "pass" if ok else "fail", f"forbidden text {'absent' if ok else 'present'}", {"value": value})

        if ctype == "text_regex":
            pattern = str(check.get("pattern", ""))
            count = len(re.findall(pattern, deliverable, flags=re.MULTILINE))
            minimum = int(check.get("min_matches", 1))
            ok = count >= minimum
            return CheckResult(ctype, "pass" if ok else "fail", f"regex matched {count} time(s); need >= {minimum}", {"pattern": pattern, "matches": count, "minimum": minimum})

        if ctype == "file_exists":
            path = _resolve(workspace, str(check["path"]))
            ok = path.is_file()
            return CheckResult(ctype, "pass" if ok else "fail", f"file {'exists' if ok else 'missing'}: {check['path']}", {"path": str(path)})

        if ctype == "file_contains":
            path = _resolve(workspace, str(check["path"]))
            if not path.is_file():
                return CheckResult(ctype, "fail", f"file missing: {check['path']}", {"path": str(path)})
            text = path.read_text(encoding="utf-8")
            value = str(check.get("contains", ""))
            ok = value in text
            return CheckResult(ctype, "pass" if ok else "fail", f"file {'contains' if ok else 'does not contain'} required text", {"path": str(path), "value": value})

        if ctype == "file_regex":
            path = _resolve(workspace, str(check["path"]))
            if not path.is_file():
                return CheckResult(ctype, "fail", f"file missing: {check['path']}", {"path": str(path)})
            text = path.read_text(encoding="utf-8")
            pattern = str(check.get("pattern", ""))
            count = len(re.findall(pattern, text, flags=re.MULTILINE))
            minimum = int(check.get("min_matches", 1))
            ok = count >= minimum
            return CheckResult(ctype, "pass" if ok else "fail", f"regex matched {count} time(s); need >= {minimum}", {"path": str(path), "pattern": pattern, "matches": count})

        if ctype == "json_equals":
            path = _resolve(workspace, str(check["path"]))
            if not path.is_file():
                return CheckResult(ctype, "fail", f"file missing: {check['path']}", {"path": str(path)})
            obj = json.loads(path.read_text(encoding="utf-8"))
            cur: Any = obj
            for part in str(check["key"]).split("."):
                if isinstance(cur, dict) and part in cur:
                    cur = cur[part]
                else:
                    return CheckResult(ctype, "fail", f"key missing: {check['key']}", {"path": str(path)})
            expected = check.get("value")
            ok = cur == expected
            return CheckResult(ctype, "pass" if ok else "fail", f"JSON value {'matches' if ok else 'does not match'} expected", {"actual": cur, "expected": expected})

        if ctype == "csv_unique":
            path = _resolve(workspace, str(check["path"]))
            column = str(check["column"])
            with path.open(newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            values = [r.get(column, "") for r in rows]
            duplicates = len(values) - len(set(values))
            ok = duplicates == 0
            return CheckResult(ctype, "pass" if ok else "fail", f"{duplicates} duplicate value(s) in {column}", {"rows": len(rows), "duplicates": duplicates, "column": column})

        if ctype == "csv_row_count":
            path = _resolve(workspace, str(check["path"]))
            with path.open(newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            expected = int(check["equals"])
            ok = len(rows) == expected
            return CheckResult(ctype, "pass" if ok else "fail", f"row count {len(rows)}; expected {expected}", {"rows": len(rows), "expected": expected})

        if ctype == "command":
            if not allow_exec:
                return CheckResult(ctype, "unknown", "command execution disabled by policy", {"policy": "deny-by-default"})
            argv = check.get("argv")
            if not isinstance(argv, list) or not argv or not all(isinstance(x, str) for x in argv):
                return CheckResult(ctype, "unknown", "invalid argv", {})
            timeout = min(int(check.get("timeout_seconds", 10)), 30)
            proc = subprocess.run(argv, cwd=workspace, capture_output=True, text=True, timeout=timeout)
            expected = int(check.get("expect_exit", 0))
            ok = proc.returncode == expected
            return CheckResult(ctype, "pass" if ok else "fail", f"command exited {proc.returncode}; expected {expected}", {
                "argv": argv,
                "returncode": proc.returncode,
                "stdout": proc.stdout[-4000:],
                "stderr": proc.stderr[-4000:],
            })

        return CheckResult(ctype or "unknown", "unknown", "unsupported check type", {"check": check})
    except Exception as exc:
        return CheckResult(ctype or "unknown", "unknown", f"check error: {exc}", {})


def verify(spec: dict[str, Any], base_dir: str | Path = ".", allow_exec: bool = False) -> dict[str, Any]:
    base = Path(base_dir).resolve()
    workspace_rel = str(spec.get("workspace", "."))
    workspace = _resolve(base, workspace_rel)
    criteria = spec.get("criteria")
    if not isinstance(criteria, list) or not criteria:
        raise VerificationError("spec.criteria must be a non-empty list")

    results: list[CriterionResult] = []
    total_weight = 0.0
    passed_weight = 0.0

    for idx, criterion in enumerate(criteria, start=1):
        cid = str(criterion.get("id", f"C{idx}"))
        text = str(criterion.get("text", cid))
        weight = float(criterion.get("weight", 1.0))
        checks_raw = criterion.get("checks", [])
        checks = [_run_check(c, spec, workspace, allow_exec) for c in checks_raw]
        statuses = {c.status for c in checks}
        if not checks or "unknown" in statuses:
            status = "unknown" if "fail" not in statuses else "fail"
        elif "fail" in statuses:
            status = "fail"
        else:
            status = "pass"
        results.append(CriterionResult(cid, text, status, weight, checks))
        total_weight += weight
        if status == "pass":
            passed_weight += weight

    score = round(100 * passed_weight / total_weight) if total_weight else 0
    counts = {s: sum(r.status == s for r in results) for s in ("pass", "fail", "unknown")}
    if counts["fail"]:
        verdict = "fail"
    elif counts["unknown"]:
        verdict = "unknown"
    else:
        verdict = "pass"

    return {
        "schema_version": "0.1",
        "task_id": spec.get("id", "ad-hoc"),
        "task": spec.get("task", ""),
        "verdict": verdict,
        "score": score,
        "counts": counts,
        "criteria": [
            {
                **{k: v for k, v in asdict(r).items() if k != "checks"},
                "checks": [asdict(c) for c in r.checks],
            }
            for r in results
        ],
        "policy": {
            "command_execution": "allowed for trusted local fixtures" if allow_exec else "disabled",
            "unknown_is_not_pass": True,
        },
    }
