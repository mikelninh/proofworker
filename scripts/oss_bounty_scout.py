#!/usr/bin/env python3
"""ProofWorker verified OSS bounty scout.

Source of truth is GitHub, not a bounty marketplace card.

v0.1 scope:
- discover open GitHub issues that explicitly integrate Opire
- verify issue state on GitHub
- read reward/try/claim commands from the issue discussion
- reject zero-bounty, unsafe, stale, reward-less, or heavily-contested work
- rank small, verifiable engineering tasks by conservative EV/hour
- write local evidence receipts

No GitHub mutations are performed. /try comments, forks, PRs, and reward claims
remain explicit human-approved actions.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

GITHUB_API = "https://api.github.com"
USER_AGENT = "ProofWorker/0.4-oss-bounty-scout"

REWARD_RE = re.compile(r"(?im)(?:^|\s)/reward\s+\$?([0-9]+(?:\.[0-9]{1,2})?)\b")
TRY_RE = re.compile(r"(?im)(?:^|\s)/try\b")
CLAIM_RE = re.compile(r"(?im)(?:^|\s)/claim(?:\s+#[0-9]+)?\b")

FIT_SIGNALS = {
    "test": 8,
    "tests": 8,
    "pytest": 8,
    "vitest": 8,
    "bug": 7,
    "fix": 7,
    "python": 6,
    "typescript": 6,
    "javascript": 6,
    "api": 5,
    "json": 5,
    "csv": 5,
    "data": 4,
    "documentation": 4,
    "readme": 4,
    "ci": 4,
    "github actions": 4,
    "validation": 4,
    "error handling": 4,
    "regression": 4,
    "coverage": 4,
    "openapi": 4,
}

SECURITY_BLOCK_SIGNALS = (
    "phishing",
    "credential theft",
    "steal credentials",
    "ransomware",
    "malware",
    "keylogger",
    "credential stuffing",
    "ddos",
    "botnet",
    "bypass authentication",
    "bypass auth",
    "exfiltrat",
    "weaponize",
    "exploit a live",
)


def receipt_dir() -> Path:
    root = os.environ.get("PROOFWORKER_CONFIG_DIR")
    base = Path(root).expanduser() if root else Path.home() / ".proofworker"
    path = base / "oss" / "receipts"
    path.mkdir(parents=True, exist_ok=True)
    return path


def github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def request_json(url: str, *, timeout: int = 20) -> Any:
    req = Request(url, headers=github_headers())
    try:
        with urlopen(req, timeout=timeout) as response:
            text = response.read().decode("utf-8")
            return json.loads(text) if text.strip() else {}
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        if exc.code == 403 and "rate limit" in body.lower():
            raise RuntimeError(
                "GitHub public API rate limit reached. Wait for reset or set GITHUB_TOKEN locally; do not paste it into chat."
            ) from exc
        raise RuntimeError(f"GitHub HTTP {exc.code}: {body[:500]}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach GitHub: {exc.reason}") from exc


def text_blob(issue: dict[str, Any]) -> str:
    labels = issue.get("labels") or []
    label_names: list[str] = []
    for label in labels:
        if isinstance(label, dict):
            label_names.append(str(label.get("name") or ""))
        else:
            label_names.append(str(label))
    return " ".join(
        [
            str(issue.get("title") or ""),
            str(issue.get("body") or ""),
            " ".join(label_names),
        ]
    ).lower()


def fit_score(text: str) -> int:
    return sum(weight for signal, weight in FIT_SIGNALS.items() if signal in text)


def security_blocked(text: str) -> bool:
    return any(signal in text for signal in SECURITY_BLOCK_SIGNALS)


def parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def age_days(issue: dict[str, Any], now: datetime | None = None) -> float:
    now = now or datetime.now(timezone.utc)
    updated = parse_dt(issue.get("updated_at")) or parse_dt(issue.get("created_at"))
    if not updated:
        return 9999.0
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=timezone.utc)
    return max(0.0, (now - updated).total_seconds() / 86400.0)


def repository_name(issue: dict[str, Any]) -> str:
    repo_url = str(issue.get("repository_url") or "")
    marker = "/repos/"
    if marker in repo_url:
        return repo_url.split(marker, 1)[1].strip("/")
    html = str(issue.get("html_url") or "")
    match = re.match(r"https://github\.com/([^/]+/[^/]+)/issues/\d+", html)
    return match.group(1) if match else "?"


def command_evidence(issue: dict[str, Any], comments: list[dict[str, Any]]) -> dict[str, Any]:
    records: list[tuple[str, str]] = [("issue-body", str(issue.get("body") or ""))]
    for comment in comments:
        user = comment.get("user") if isinstance(comment.get("user"), dict) else {}
        login = str(user.get("login") or "unknown")
        records.append((login, str(comment.get("body") or "")))

    rewards: list[dict[str, Any]] = []
    triers: set[str] = set()
    claimers: set[str] = set()
    for actor, body in records:
        for match in REWARD_RE.finditer(body):
            amount = float(match.group(1))
            if 0 < amount <= 100000:
                rewards.append({"actor": actor, "amount": round(amount, 2)})
        if TRY_RE.search(body):
            triers.add(actor)
        if CLAIM_RE.search(body):
            claimers.add(actor)

    return {
        "reward_commands": rewards,
        "verified_reward": round(sum(item["amount"] for item in rewards), 2),
        "try_count": len(triers),
        "claim_count": len(claimers),
        "triers": sorted(triers),
        "claimers": sorted(claimers),
    }


def estimated_hours(issue: dict[str, Any], text: str) -> float:
    if "documentation" in text or "readme" in text or "translation" in text:
        base = 1.5
    elif "test" in text or "coverage" in text or "ci" in text:
        base = 2.5
    elif "bug" in text or "fix" in text or "error handling" in text:
        base = 3.0
    elif "feature" in text or "implement" in text:
        base = 5.0
    else:
        base = 4.0

    body_len = len(str(issue.get("body") or ""))
    if body_len > 5000:
        base *= 1.25
    return round(min(max(base, 1.0), 12.0), 2)


def score_verified_issue(
    issue: dict[str, Any],
    comments: list[dict[str, Any]],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    text = text_blob(issue)
    evidence = command_evidence(issue, comments)
    reward = float(evidence["verified_reward"])
    fit = fit_score(text)
    days = age_days(issue, now)
    hours = estimated_hours(issue, text)
    labels = {
        str(label.get("name") or "").lower()
        for label in (issue.get("labels") or [])
        if isinstance(label, dict)
    }

    risks: list[str] = []
    action = "REVIEW"

    if str(issue.get("state") or "").lower() != "open":
        risks.append("github-issue-not-open")
        action = "SKIP"
    if "zero-bounty" in labels or "zero bounty" in labels:
        risks.append("explicit-zero-bounty")
        action = "SKIP"
    if security_blocked(text):
        risks.append("security-sensitive/blocked")
        action = "SKIP"
    if reward <= 0:
        risks.append("no-github-verified-reward-command")
        action = "SKIP"
    if days > 365:
        risks.append("stale-over-365d")
        if action != "SKIP":
            action = "REVIEW"
    elif days > 180:
        risks.append("stale-over-180d")
    if evidence["claim_count"]:
        risks.append("existing-claim-evidence")
        if action != "SKIP":
            action = "REVIEW"
    if evidence["try_count"] >= 5:
        risks.append("high-competition")
        if action != "SKIP":
            action = "REVIEW"
    elif evidence["try_count"] >= 2:
        risks.append("competition-present")
    if reward > 5000:
        risks.append("reward-anomaly-manual-review")
        if action != "SKIP":
            action = "REVIEW"

    competition_factor = 1.0 / (1.0 + 0.35 * float(evidence["try_count"]))
    freshness_factor = 1.0 if days <= 30 else 0.85 if days <= 90 else 0.65 if days <= 180 else 0.4
    fit_factor = min(1.0, 0.35 + fit / 45.0)
    conservative_win = min(0.45, 0.18 * competition_factor * freshness_factor * fit_factor)
    expected_value = reward * conservative_win
    ev_per_hour = expected_value / hours if hours else 0.0
    score = ev_per_hour + fit * 0.25

    if (
        action != "SKIP"
        and reward >= 50
        and fit >= 8
        and evidence["try_count"] <= 2
        and evidence["claim_count"] == 0
        and days <= 180
        and reward <= 5000
    ):
        action = "QUALIFY"
    elif action != "SKIP":
        action = "REVIEW"

    return {
        "source": "github-verified-opire",
        "repo": repository_name(issue),
        "number": issue.get("number"),
        "title": str(issue.get("title") or "(untitled)"),
        "url": str(issue.get("html_url") or ""),
        "action": action,
        "verified_reward": round(reward, 2),
        "fit": fit,
        "age_days": round(days, 1),
        "estimated_hours": hours,
        "try_count": int(evidence["try_count"]),
        "claim_count": int(evidence["claim_count"]),
        "win_probability_heuristic": round(conservative_win, 3),
        "expected_value": round(expected_value, 2),
        "ev_per_hour": round(ev_per_hour, 2),
        "score": round(score, 2),
        "risk_flags": list(dict.fromkeys(risks)),
        "reward_commands": evidence["reward_commands"],
        "issue": issue,
    }


def fetch_comments(issue: dict[str, Any], *, limit: int = 100) -> list[dict[str, Any]]:
    url = str(issue.get("comments_url") or "")
    if not url:
        return []
    sep = "&" if "?" in url else "?"
    payload = request_json(f"{url}{sep}per_page={min(limit, 100)}")
    return [item for item in payload if isinstance(item, dict)] if isinstance(payload, list) else []


def discover_opire_issues(*, max_issues: int = 25) -> list[dict[str, Any]]:
    query = 'is:issue is:open "This repo is using Opire"'
    params = urlencode(
        {
            "q": query,
            "sort": "updated",
            "order": "desc",
            "per_page": min(max(max_issues * 2, 30), 100),
        }
    )
    payload = request_json(f"{GITHUB_API}/search/issues?{params}")
    items = payload.get("items", []) if isinstance(payload, dict) else []
    issues = [item for item in items if isinstance(item, dict) and "pull_request" not in item]

    # Spend comment API calls only on issues that have some task fit and are not
    # obviously security-sensitive. This keeps the unauthenticated rate budget bounded.
    issues.sort(key=lambda item: fit_score(text_blob(item)), reverse=True)
    return issues[:max_issues]


def scan(*, top: int = 15, max_issues: int = 25) -> list[dict[str, Any]]:
    discovered = discover_opire_issues(max_issues=max_issues)
    results: list[dict[str, Any]] = []
    for issue in discovered:
        text = text_blob(issue)
        if security_blocked(text):
            comments: list[dict[str, Any]] = []
        else:
            try:
                comments = fetch_comments(issue)
            except RuntimeError as exc:
                result = score_verified_issue(issue, [])
                result["action"] = "REVIEW" if result["action"] != "SKIP" else "SKIP"
                result["risk_flags"].append(f"comments-unavailable:{str(exc)[:80]}")
                results.append(result)
                continue
        results.append(score_verified_issue(issue, comments))

    results.sort(
        key=lambda item: (
            2 if item["action"] == "QUALIFY" else 1 if item["action"] == "REVIEW" else 0,
            float(item["score"]),
        ),
        reverse=True,
    )
    return results[:top]


def write_receipt(items: list[dict[str, Any]]) -> tuple[Path, Path]:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    md_path = receipt_dir() / f"oss-bounty-scan-{stamp}.md"
    json_path = receipt_dir() / f"oss-bounty-scan-{stamp}.json"

    json_safe = []
    for item in items:
        copy = {k: v for k, v in item.items() if k != "issue"}
        json_safe.append(copy)
    json_path.write_text(json.dumps(json_safe, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# ProofWorker verified OSS bounty scan",
        "",
        "GitHub is the source of truth. Marketplace headline values are not treated as verified reward.",
        "",
    ]
    for idx, item in enumerate(items, 1):
        lines += [
            f"## {idx}. {item['action']} — {item['repo']}#{item['number']}",
            f"- Title: {item['title']}",
            f"- GitHub: {item['url']}",
            f"- Verified reward commands: ${item['verified_reward']:.2f}",
            f"- Tries: {item['try_count']} | Claims: {item['claim_count']}",
            f"- Age: {item['age_days']}d | Fit: {item['fit']} | EV/h heuristic: ${item['ev_per_hour']:.2f}",
            f"- Risks: {', '.join(item['risk_flags']) or 'none'}",
            "",
        ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path, json_path


def print_scan(items: list[dict[str, Any]]) -> None:
    print("\nProofWorker verified OSS bounty scan")
    print("GitHub issue state + explicit reward commands are the source of truth.\n")
    if not items:
        print("No candidate Opire issues found.")
        return
    for idx, item in enumerate(items, 1):
        print(
            f"{idx:2}. {item['action']:<7} score={item['score']:6.2f}  "
            f"EV/h=${item['ev_per_hour']:6.2f}  reward=${item['verified_reward']:7.2f}  "
            f"tries={item['try_count']:2}  {item['repo']}#{item['number']} — {item['title']}"
        )
        print(f"    age={item['age_days']}d fit={item['fit']} risk={', '.join(item['risk_flags']) or 'none'}")
        print(f"    {item['url']}")


def self_test() -> int:
    now = datetime(2026, 9, 8, tzinfo=timezone.utc)
    issue = {
        "number": 42,
        "title": "Fix pagination bug and add regression tests",
        "body": "This repo is using Opire. Please fix the Python API pagination bug and add tests.",
        "state": "open",
        "updated_at": "2026-09-01T00:00:00Z",
        "repository_url": "https://api.github.com/repos/acme/api",
        "html_url": "https://github.com/acme/api/issues/42",
        "labels": [{"name": "bug"}],
    }
    comments = [
        {"user": {"login": "sponsor"}, "body": "/reward 120"},
        {"user": {"login": "worker-a"}, "body": "/try"},
    ]
    result = score_verified_issue(issue, comments, now=now)
    assert result["verified_reward"] == 120.0, result
    assert result["try_count"] == 1, result
    assert result["action"] == "QUALIFY", result
    assert result["repo"] == "acme/api"

    zero = dict(issue)
    zero["labels"] = [{"name": "zero-bounty"}]
    zero_result = score_verified_issue(zero, comments, now=now)
    assert zero_result["action"] == "SKIP", zero_result
    assert "explicit-zero-bounty" in zero_result["risk_flags"]

    closed = dict(issue)
    closed["state"] = "closed"
    closed_result = score_verified_issue(closed, comments, now=now)
    assert closed_result["action"] == "SKIP", closed_result

    no_reward = score_verified_issue(issue, [], now=now)
    assert no_reward["action"] == "SKIP", no_reward
    assert "no-github-verified-reward-command" in no_reward["risk_flags"]

    unsafe = dict(issue)
    unsafe["title"] = "Build credential phishing malware"
    unsafe_result = score_verified_issue(unsafe, comments, now=now)
    assert unsafe_result["action"] == "SKIP", unsafe_result
    assert "security-sensitive/blocked" in unsafe_result["risk_flags"]

    anomalous = list(comments) + [{"user": {"login": "sponsor2"}, "body": "/reward 9000"}]
    anomalous_result = score_verified_issue(issue, anomalous, now=now)
    assert anomalous_result["action"] == "REVIEW", anomalous_result
    assert "reward-anomaly-manual-review" in anomalous_result["risk_flags"]

    print("OSS BOUNTY SCOUT SELF-TEST PASS")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ProofWorker verified OSS bounty scout")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test")
    scan_p = sub.add_parser("scan")
    scan_p.add_argument("--top", type=int, default=15)
    scan_p.add_argument("--max-issues", type=int, default=25)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "self-test":
        return self_test()
    if args.command == "scan":
        try:
            items = scan(top=max(1, args.top), max_issues=max(1, min(args.max_issues, 40)))
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        print_scan(items)
        md_path, json_path = write_receipt(items)
        print(f"\nReceipt: {md_path}")
        print(f"JSON:    {json_path}")
        qualifies = [item for item in items if item["action"] == "QUALIFY"]
        if qualifies:
            print("\nQualified OSS candidates require human review before /try, fork, PR, or claim actions.")
        else:
            print("\nNo GitHub-verified bounty clears the current gate.")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
