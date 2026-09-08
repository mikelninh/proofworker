#!/usr/bin/env python3
"""ProofWorker bounded revenue operator.

Purpose:
- scan Dealwork's public job feed (including microtasks)
- remove obvious marketplace noise and unsafe work
- rank opportunities by a transparent expected-value heuristic
- produce evidence-friendly bid drafts
- optionally submit a bid only after a per-job human confirmation

This is intentionally not a general autonomous spending/contract agent.
Claims, wallet actions, contract acceptance, deliverable submission and escrow
operations are not implemented here.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import re
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DEFAULT_BASE_URL = "https://dealwork.ai/api/v1"
DEFAULT_TOP = 12

FIT_SIGNALS = {
    "qa": 8,
    "verify": 8,
    "verification": 8,
    "test": 6,
    "review": 6,
    "audit": 5,
    "acceptance": 5,
    "bug": 4,
    "fix": 4,
    "python": 3,
    "javascript": 3,
    "typescript": 3,
    "api": 3,
    "research": 4,
    "citation": 5,
    "data": 4,
    "csv": 4,
    "json": 3,
    "documentation": 3,
    "readme": 3,
    "analyze": 2,
    "analysis": 2,
}

TASK_SIGNALS = (
    "fix ", "fix:", "bug", "implement", "add ", "review", "audit", "verify",
    "test", "write", "document", "analyze", "analyse", "clean", "convert",
    "investigate", "refactor", "migrate", "update", "create",
)

PROVIDER_NOISE_SIGNALS = (
    "full-stack ai agent", "ai agent team", "income agent", "hire me",
    "available for", "services:", "service:", "we offer", "i offer",
    "research & technical writing", "code review, python dev",
    "research, web scraping, qa", "research, technical writing, data analysis",
)

SECURITY_BLOCK_SIGNALS = (
    "phishing", "steal credentials", "credential theft", "malware", "ransomware",
    "ddos", "botnet", "bypass authentication", "bypass auth", "exfiltrat",
    "weaponize", "keylogger", "credential stuffing", "exploit a live",
)

REAL_WORLD_REVIEW_SIGNALS = (
    "make a phone call", "call this number", "purchase", "buy this", "physical visit",
    "visit in person", "log in to my account", "use my credentials",
)


def config_dir() -> Path:
    override = os.environ.get("PROOFWORKER_CONFIG_DIR")
    return Path(override).expanduser() if override else Path.home() / ".proofworker" / "dealwork"


def credentials_path() -> Path:
    return config_dir() / "credentials.json"


def read_credentials() -> dict[str, Any] | None:
    path = credentials_path()
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if payload.get("apiKey") and payload.get("agentAccountId"):
        return payload
    return None


def request_json(
    base_url: str,
    method: str,
    path: str,
    *,
    body: dict[str, Any] | None = None,
    bearer: str | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    raw = None if body is None else json.dumps(body, separators=(",", ":")).encode("utf-8")
    headers = {"Accept": "application/json", "User-Agent": "ProofWorker/0.3-revenue-loop"}
    if raw is not None:
        headers["Content-Type"] = "application/json"
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    req = Request(f"{base_url.rstrip('/')}/{path.lstrip('/')}", data=raw, headers=headers, method=method)
    try:
        with urlopen(req, timeout=timeout) as response:
            text = response.read().decode("utf-8")
            return json.loads(text) if text.strip() else {}
    except HTTPError as exc:
        payload = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Dealwork HTTP {exc.code}: {payload[:700]}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach Dealwork: {exc.reason}") from exc


def data_object(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data", payload)
    return data if isinstance(data, dict) else {}


def data_list(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data", payload)
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("items", "jobs", "listings", "results", "bids", "contracts"):
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def text_blob(job: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in (
        "title", "description", "category", "tags", "acceptanceCriteria",
        "acceptance_criteria", "deliverables", "requirements", "skills",
    ):
        value = job.get(key)
        if isinstance(value, (dict, list)):
            parts.append(json.dumps(value, sort_keys=True, ensure_ascii=False))
        elif value is not None:
            parts.append(str(value))
    return " ".join(parts).lower()


def money(job: dict[str, Any]) -> float:
    for key in ("fixedPrice", "budgetMax", "budget", "price", "amount"):
        value = job.get(key)
        if value is None:
            continue
        try:
            return max(0.0, float(str(value).replace("$", "").replace(",", "").strip()))
        except ValueError:
            continue
    return 0.0


def bid_count(distribution: dict[str, Any] | None) -> int | None:
    if not distribution:
        return None
    candidates = [
        distribution.get("count"),
        distribution.get("total"),
        distribution.get("bidCount"),
        distribution.get("bid_count"),
    ]
    data = distribution.get("data")
    if isinstance(data, dict):
        candidates += [data.get("count"), data.get("total"), data.get("bidCount"), data.get("bid_count")]
    for value in candidates:
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            pass
    return None


def provider_noise(text: str) -> bool:
    return any(signal in text for signal in PROVIDER_NOISE_SIGNALS)


def security_blocked(text: str) -> bool:
    return any(signal in text for signal in SECURITY_BLOCK_SIGNALS)


def real_world_review(text: str) -> bool:
    return any(signal in text for signal in REAL_WORLD_REVIEW_SIGNALS)


def fit_score(text: str) -> int:
    return sum(weight for signal, weight in FIT_SIGNALS.items() if signal in text)


def task_clarity(job: dict[str, Any], text: str) -> float:
    score = 0.0
    description = str(job.get("description", ""))
    if len(description.strip()) >= 100:
        score += 0.12
    if any(job.get(k) for k in ("acceptanceCriteria", "acceptance_criteria", "deliverables", "requirements")):
        score += 0.18
    if "acceptance criteria" in text or "deliverable" in text:
        score += 0.08
    if any(signal in text for signal in TASK_SIGNALS):
        score += 0.08
    return min(score, 0.35)


def estimated_hours(job: dict[str, Any], text: str) -> float:
    budget = money(job)
    if "review" in text or "audit" in text or "verify" in text:
        base = 1.25
    elif "research" in text or "documentation" in text or "readme" in text:
        base = 1.5
    elif "data" in text or "csv" in text or "json" in text:
        base = 1.25
    elif any(k in text for k in ("bug", "fix", "python", "typescript", "javascript", "api")):
        base = 2.0
    else:
        base = 2.5

    if budget >= 100:
        base *= 1.6
    elif budget >= 50:
        base *= 1.25
    return round(max(0.5, min(base, 8.0)), 2)


def score_job(job: dict[str, Any], distribution: dict[str, Any] | None = None) -> dict[str, Any]:
    text = text_blob(job)
    budget = money(job)
    fit = fit_score(text)
    noise = provider_noise(text)
    blocked = security_blocked(text)
    real_world = real_world_review(text)
    bids = bid_count(distribution)
    hours = estimated_hours(job, text)

    probability = 0.30
    probability += task_clarity(job, text)
    probability += min(0.16, fit / 180.0)
    if budget and budget <= 50:
        probability += 0.05
    if bids is not None:
        if bids == 0:
            probability += 0.08
        elif bids <= 3:
            probability += 0.03
        elif bids >= 10:
            probability -= 0.14
        elif bids >= 6:
            probability -= 0.08
    if noise:
        probability -= 0.28
    if real_world:
        probability -= 0.15
    if blocked:
        probability = 0.0
    probability = max(0.0, min(0.80, probability))

    conservative_net = budget * 0.90
    expected_net = conservative_net * probability
    ev_per_hour = expected_net / hours if hours else 0.0

    risk_flags: list[str] = []
    if blocked:
        risk_flags.append("security-sensitive/blocked")
    if real_world:
        risk_flags.append("requires-human-review")
    code_like = any(k in text for k in ("python", "javascript", "typescript", "node", "code", "repo"))
    if code_like:
        risk_flags.append("sandbox-before-untrusted-exec")
    if noise:
        risk_flags.append("provider-advertisement/noise-likely")
    if budget <= 0:
        risk_flags.append("no-usable-budget")

    score = ev_per_hour + fit * 0.35
    if noise:
        score -= 18
    if real_world:
        score -= 8
    if blocked:
        score = -999
    if budget <= 0:
        score -= 20

    if blocked or budget <= 0 or noise:
        action = "SKIP"
    elif real_world:
        action = "REVIEW"
    elif fit >= 12 and expected_net >= 3:
        action = "QUALIFY"
    else:
        action = "REVIEW"

    return {
        "id": str(job.get("id") or job.get("jobId") or "?"),
        "title": str(job.get("title") or "(untitled)"),
        "budget": round(budget, 2),
        "fit": fit,
        "bid_count": bids,
        "estimated_hours": hours,
        "acceptance_probability_heuristic": round(probability, 3),
        "expected_net_after_10pct_fee": round(expected_net, 2),
        "ev_per_hour": round(ev_per_hour, 2),
        "score": round(score, 2),
        "action": action,
        "risk_flags": risk_flags,
        "job": job,
    }


def suggested_bid_amount(opportunity: dict[str, Any]) -> float:
    budget = float(opportunity["budget"])
    if budget <= 10:
        factor = 1.0
    elif budget <= 50:
        factor = 0.90
    else:
        factor = 0.95
    return round(max(1.0, min(budget, budget * factor)), 2)


def proposal_for(opportunity: dict[str, Any]) -> str:
    text = text_blob(opportunity["job"])
    if "review" in text or "audit" in text or "qa" in text:
        core = (
            "I can handle this as an evidence-first QA pass: reproduce the issue where safe, "
            "review the relevant code/API behavior, return prioritized findings, make a minimal "
            "patch when the brief requires it, and attach tests/checks that show what passes, "
            "fails, or remains unknown."
        )
    elif "research" in text or "citation" in text:
        core = (
            "I can deliver a sourced research pass with claim-to-source mapping, freshness checks, "
            "unsupported-claim flags, and a concise evidence summary rather than relying on unsupported confidence."
        )
    elif "data" in text or "csv" in text or "json" in text:
        core = (
            "I can deliver this with reconciliation evidence: schema/invariant checks, duplicate/null handling, "
            "before/after counts, and a compact change log so the result is independently checkable."
        )
    else:
        core = (
            "I can execute this against the stated acceptance criteria and return a compact evidence pack "
            "showing exactly what was verified, what failed, and what remains unknown."
        )
    return (
        core
        + " I use ProofWorker as an independent verification gate before submission, so I will not mark a criterion "
          "complete without evidence. I will keep scope narrow and communicate immediately if the brief requires access "
          "or execution that cannot be safely verified."
    )


def ranked_jobs(base_url: str, *, include_microtasks: bool = True, max_pages: int = 3) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    for page in range(1, max_pages + 1):
        qs = urlencode({
            "page": page,
            "per_page": 100,
            "include_microtasks": str(include_microtasks).lower(),
        })
        payload = request_json(base_url, "GET", f"jobs?{qs}")
        chunk = data_list(payload)
        jobs.extend(chunk)
        meta = payload.get("meta", {})
        total = meta.get("total") if isinstance(meta, dict) else None
        if not chunk:
            break
        if total is not None and len(jobs) >= int(total):
            break
        if len(chunk) < 100:
            break

    scored: list[dict[str, Any]] = []
    for job in jobs:
        job_id = str(job.get("id") or job.get("jobId") or "")
        detail = job
        distribution: dict[str, Any] | None = None
        if job_id:
            try:
                detail_payload = request_json(base_url, "GET", f"jobs/{job_id}", timeout=12)
                candidate = data_object(detail_payload)
                if candidate:
                    detail = candidate
            except RuntimeError:
                pass
            try:
                distribution = request_json(base_url, "GET", f"jobs/{job_id}/bids/distribution", timeout=12)
            except RuntimeError:
                distribution = None
        scored.append(score_job(detail, distribution))
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored


def receipt_dir() -> Path:
    path = config_dir() / "receipts"
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_receipt(items: list[dict[str, Any]]) -> tuple[Path, Path]:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    json_path = receipt_dir() / f"market-scan-{stamp}.json"
    md_path = receipt_dir() / f"market-scan-{stamp}.md"

    safe_items = []
    for item in items:
        safe_items.append({k: v for k, v in item.items() if k != "job"})
    json_path.write_text(json.dumps(safe_items, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# ProofWorker Market Scan",
        "",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "> Scores and acceptance probabilities are heuristics for prioritization, not guarantees.",
        "",
        "| Action | EV/h | Expected net | Budget | Fit | Bids | Job |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for item in items:
        bids = "?" if item["bid_count"] is None else str(item["bid_count"])
        title = item["title"].replace("|", "\\|")
        lines.append(
            f"| {item['action']} | ${item['ev_per_hour']:.2f} | ${item['expected_net_after_10pct_fee']:.2f} "
            f"| ${item['budget']:.2f} | {item['fit']} | {bids} | {title} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def print_table(items: list[dict[str, Any]], top: int) -> None:
    print("\nProofWorker revenue scan")
    print("Scores are prioritization heuristics, not calibrated win probabilities.\n")
    for idx, item in enumerate(items[:top], 1):
        bids = "?" if item["bid_count"] is None else item["bid_count"]
        flags = ", ".join(item["risk_flags"]) or "none"
        print(
            f"{idx:>2}. {item['action']:<7} score={item['score']:>6.2f}  "
            f"EV/h=${item['ev_per_hour']:>6.2f}  exp=${item['expected_net_after_10pct_fee']:>6.2f}  "
            f"budget=${item['budget']:>7.2f}  bids={str(bids):>3}  {item['title']}"
        )
        print(f"    id={item['id']}  fit={item['fit']}  est={item['estimated_hours']}h  risk={flags}")


def derive_openapi_url(base_url: str) -> str:
    marker = "/api/v1"
    if marker in base_url:
        return base_url.split(marker, 1)[0].rstrip("/") + "/openapi.json"
    return base_url.rstrip("/") + "/openapi.json"


def fetch_absolute_json(url: str, timeout: int = 30) -> dict[str, Any]:
    req = Request(url, headers={"Accept": "application/json", "User-Agent": "ProofWorker/0.3-revenue-loop"})
    try:
        with urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Could not read Dealwork OpenAPI schema: {exc}") from exc


def resolve_schema(spec: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    seen: set[str] = set()
    current = schema
    for _ in range(8):
        ref = current.get("$ref") if isinstance(current, dict) else None
        if not ref or not ref.startswith("#/"):
            return current if isinstance(current, dict) else {}
        if ref in seen:
            return {}
        seen.add(ref)
        target: Any = spec
        for part in ref[2:].split("/"):
            if not isinstance(target, dict):
                return {}
            target = target.get(part)
        current = target if isinstance(target, dict) else {}
    return current if isinstance(current, dict) else {}


def create_bid_schema(base_url: str) -> dict[str, Any]:
    spec = fetch_absolute_json(derive_openapi_url(base_url))
    path = spec.get("paths", {}).get("/jobs/{id}/bids", {})
    post = path.get("post", {}) if isinstance(path, dict) else {}
    request_body = post.get("requestBody", {}) if isinstance(post, dict) else {}
    content = request_body.get("content", {}) if isinstance(request_body, dict) else {}
    app_json = content.get("application/json", {}) if isinstance(content, dict) else {}
    schema = app_json.get("schema", {}) if isinstance(app_json, dict) else {}
    resolved = resolve_schema(spec, schema if isinstance(schema, dict) else {})
    if not resolved:
        raise RuntimeError("Dealwork OpenAPI did not expose a usable CreateBid request schema.")
    return resolved


def normalized(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def bid_payload_from_schema(
    schema: dict[str, Any],
    opportunity: dict[str, Any],
    credentials: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    props = schema.get("properties", {})
    required = set(schema.get("required", []))
    if not isinstance(props, dict):
        props = {}
    proposal = proposal_for(opportunity)
    amount = suggested_bid_amount(opportunity)
    delivery_hours = max(1, int(math.ceil(float(opportunity["estimated_hours"]))))

    payload: dict[str, Any] = {}
    for name, field_schema in props.items():
        key = normalized(str(name))
        field_schema = field_schema if isinstance(field_schema, dict) else {}
        typ = field_schema.get("type")

        value: Any | None = None
        if key in {"amount", "bidamount", "price", "proposedprice", "proposedamount", "fixedprice"}:
            value = amount if typ in {"number", "integer"} else f"{amount:.2f}"
        elif key in {"proposal", "message", "coverletter", "description", "note", "bidmessage"}:
            value = proposal
        elif key in {"estimateddeliveryhours", "deliveryhours", "estimatedhours", "etahours"}:
            value = delivery_hours
        elif key in {"deliverytime", "estimateddeliverytime", "eta"}:
            value = f"{delivery_hours} hours"
        elif key == "currency":
            value = "USD"
        elif key in {"agentaccountid", "agentid", "bidderid"}:
            value = credentials.get("agentAccountId")
        elif "revision" in key:
            value = 1 if typ in {"integer", "number"} else "1"

        if value is not None:
            payload[str(name)] = value

    missing = sorted(str(name) for name in required if name not in payload)
    return payload, missing


def submit_bid(
    base_url: str,
    opportunity: dict[str, Any],
    credentials: dict[str, Any],
    *,
    require_confirmation: bool = True,
) -> dict[str, Any] | None:
    if opportunity["action"] != "QUALIFY":
        print(f"Refusing to bid: opportunity action is {opportunity['action']}, not QUALIFY.")
        return None
    if opportunity["risk_flags"] and any("blocked" in f for f in opportunity["risk_flags"]):
        print("Refusing to bid: blocked risk flag.")
        return None

    schema = create_bid_schema(base_url)
    payload, missing = bid_payload_from_schema(schema, opportunity, credentials)
    if missing:
        print("\nBid schema changed or contains fields ProofWorker will not guess.")
        print("Required fields not safely mapped:", ", ".join(missing))
        print("No bid was submitted.")
        return None

    print("\nA3 BID PREVIEW")
    print(f"Job: {opportunity['title']}")
    print(f"Job ID: {opportunity['id']}")
    print(f"Budget: ${opportunity['budget']:.2f}")
    print(f"Suggested bid: ${suggested_bid_amount(opportunity):.2f}")
    print(f"Estimated work: {opportunity['estimated_hours']}h")
    print(f"Risk flags: {', '.join(opportunity['risk_flags']) or 'none'}")
    print("\nProposal:\n")
    print(proposal_for(opportunity))
    print("\nPayload fields:", ", ".join(sorted(payload)))

    if require_confirmation:
        token = f"BID {opportunity['id']}"
        answer = input(f"\nType exactly '{token}' to submit, or press Enter to skip:\n> ").strip()
        if answer != token:
            print("Skipped. No bid submitted.")
            return None

    api_key = str(credentials["apiKey"])
    response = request_json(
        base_url,
        "POST",
        f"jobs/{opportunity['id']}/bids",
        bearer=api_key,
        body=payload,
        timeout=30,
    )
    bid = data_object(response)
    print("Bid submitted.")
    print("Bid ID:", bid.get("id") or bid.get("bidId") or "unknown")
    return bid


def status(base_url: str) -> int:
    creds = read_credentials()
    if not creds:
        print(f"No Dealwork credentials found at {credentials_path()}")
        print("Run: python scripts/dealwork_connect.py --publish-listing")
        return 1

    key = str(creds["apiKey"])
    print(f"Agent ID: {creds['agentAccountId']}")
    for label, path in (
        ("My bids", "bids/mine"),
        ("Contracts", "contracts"),
        ("Pending listing requests", "listings/requests/pending"),
        ("Earnings", "wallet/earnings"),
    ):
        try:
            payload = request_json(base_url, "GET", path, bearer=key, timeout=15)
            items = data_list(payload)
            if items:
                print(f"{label}: {len(items)}")
                for item in items[:5]:
                    ident = item.get("id") or item.get("bidId") or item.get("contractId") or "?"
                    state = item.get("status") or item.get("state") or "?"
                    print(f"  {ident}  {state}")
            else:
                data = payload.get("data", payload)
                if isinstance(data, dict) and data:
                    safe = {k: v for k, v in data.items() if "key" not in k.lower() and "secret" not in k.lower()}
                    print(f"{label}: {json.dumps(safe, ensure_ascii=False)[:350]}")
                else:
                    print(f"{label}: 0")
        except RuntimeError as exc:
            print(f"{label}: unavailable ({exc})")
    return 0


def self_test() -> int:
    buyer_job = {
        "id": "j1",
        "title": "Fix API pagination bug and add tests",
        "description": "Fix the pagination bug. Acceptance criteria: tests pass and invalid page values return 400.",
        "budgetMax": "30.00",
        "tags": ["python", "api", "testing"],
        "acceptanceCriteria": ["tests pass", "bad page returns 400"],
    }
    noise_job = {
        "id": "j2",
        "title": "Birbus — Full-Stack AI Agent Team: Python, Go, Research & Technical Writing ($10-$100)",
        "fixedPrice": "25",
        "description": "Available for development and research services.",
    }
    blocked_job = {
        "id": "j3",
        "title": "Build credential phishing kit",
        "fixedPrice": "100",
        "description": "Bypass authentication and steal credentials.",
    }
    a = score_job(buyer_job, {"data": {"count": 1}})
    b = score_job(noise_job, {"data": {"count": 0}})
    c = score_job(blocked_job, {"data": {"count": 0}})
    assert a["action"] == "QUALIFY", a
    assert b["action"] == "SKIP", b
    assert c["action"] == "SKIP", c
    assert suggested_bid_amount(a) <= a["budget"]
    assert "ProofWorker" in proposal_for(a)
    print("SELF-TEST PASS")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bounded revenue operator for ProofWorker.")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("DEALWORK_BASE_URL", DEFAULT_BASE_URL),
        help=f"Dealwork API base URL (default: {DEFAULT_BASE_URL})",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="Read, rank and save current Dealwork opportunities.")
    scan.add_argument("--top", type=int, default=DEFAULT_TOP)
    scan.add_argument("--no-microtasks", action="store_true")
    scan.add_argument("--pages", type=int, default=3)

    run = sub.add_parser("run", help="Scan, preview top qualified bids, optionally submit with per-job confirmation.")
    run.add_argument("--top", type=int, default=5)
    run.add_argument("--attempts", type=int, default=3)
    run.add_argument("--execute", action="store_true", help="Enable interactive A3 bid submission.")
    run.add_argument("--no-microtasks", action="store_true")
    run.add_argument("--pages", type=int, default=3)

    sub.add_parser("status", help="Read current bids, contracts, listing requests and earnings.")
    sub.add_parser("self-test", help="Run deterministic no-network policy/scoring tests.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "self-test":
        return self_test()
    if args.command == "status":
        return status(args.base_url)

    items = ranked_jobs(
        args.base_url,
        include_microtasks=not args.no_microtasks,
        max_pages=max(1, min(args.pages, 10)),
    )
    if not items:
        print("No jobs returned.")
        return 0

    print_table(items, args.top)
    json_receipt, md_receipt = write_receipt(items[: max(args.top, 20)])
    print(f"\nReceipt: {md_receipt}")
    print(f"JSON:    {json_receipt}")

    if args.command == "scan":
        return 0

    qualified = [item for item in items if item["action"] == "QUALIFY"]
    if not qualified:
        print("\nNo qualified opportunities clear the current gate. No bids attempted.")
        return 0

    print("\nTop bid drafts")
    for item in qualified[: args.attempts]:
        print(f"\n--- {item['title']} [{item['id']}] ---")
        print(f"Suggested bid: ${suggested_bid_amount(item):.2f}")
        print(proposal_for(item))

    if not args.execute:
        print("\nDry run only. Add --execute to enable per-job human-confirmed bid submission.")
        return 0

    creds = read_credentials()
    if not creds:
        print(f"\nNo Dealwork credentials found at {credentials_path()}", file=sys.stderr)
        return 1

    submitted = 0
    for item in qualified[: args.attempts]:
        try:
            result = submit_bid(args.base_url, item, creds, require_confirmation=True)
            if result is not None:
                submitted += 1
        except RuntimeError as exc:
            print(f"Bid failed safely for {item['id']}: {exc}", file=sys.stderr)
    print(f"\nSubmitted bids: {submitted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
