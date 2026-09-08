#!/usr/bin/env python3
"""ProofWorker live revenue guard v3.

Default-deny live bidding: a Dealwork post may QUALIFY only when there is
positive evidence of buyer intent for a concrete task. Structured acceptance
criteria alone are not buyer evidence because supply-side service ads may carry
them too.

The live bid payload also carries Dealwork runtime aliases observed from the
current validator. This keeps bidding fail-safe when the published OpenAPI
schema temporarily lags the runtime request contract.
"""
from __future__ import annotations

import re

import revenue_operator_live_v2 as v2

live = v2.live
ro = live.ro

_OLD_SELF_TEST = ro.self_test
_OLD_SCORE = ro.score_job
_OLD_BID_PAYLOAD = ro.bid_payload_from_schema
_OLD_PROPOSAL = ro.proposal_for


_SELLER_MARKERS = (
    "i am corbin",
    "i am a transparent ai agent",
    "transparent ai agent",
    "professional ai agent",
    "autonomous ai agent",
    "what i deliver",
    "what we deliver",
    "my services",
    "our services",
    "services include",
    "service includes",
    "i work from",
    "we work from",
    "typical turnaround",
    "turnaround:",
    "pricing:",
    "pricing (",
    "usdc via escrow",
    "ready to take orders",
    "open for work",
    "available for work",
    "hire me",
    "[svc:",
)

_BUYER_REQUEST_MARKERS = (
    "i need someone",
    "we need someone",
    "i need help",
    "we need help",
    "looking for someone",
    "looking to hire",
    "please fix",
    "please build",
    "please create",
    "please write",
    "please review",
    "please audit",
    "please analyze",
    "please analyse",
    "please update",
    "your task is to",
    "task is to",
    "need this fixed",
    "need this built",
    "need this reviewed",
    "need this analyzed",
    "need this analysed",
)

_CONCRETE_OBJECT_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\brepository\b",
        r"\brepo\b",
        r"\bgithub\b",
        r"\bcodebase\b",
        r"\bexisting app\b",
        r"\bexisting code\b",
        r"\bapi endpoint\b",
        r"\bthis api\b",
        r"\bthis file\b",
        r"\bprovided file\b",
        r"\battached file\b",
        r"\bdataset\b",
        r"\bthis dataset\b",
        r"\bprovided data\b",
        r"\bcsv\b",
        r"\bspreadsheet\b",
        r"\bsource document\b",
        r"\bthis document\b",
        r"\burl\b",
        r"\bissue\s*#\d+",
        r"\bbug\b",
        r"\bfixture\b",
        r"\btest suite\b",
    )
)

_IMPERATIVE_TITLE = re.compile(
    r"^\s*(fix|build|create|write|review|audit|analy[sz]e|update|implement|debug|"
    r"generate|convert|clean|refactor|migrate|document)\b",
    re.IGNORECASE,
)


def _combined(job: dict) -> str:
    return f"{job.get('title', '')} {job.get('description', '')}".lower()


def _positive_buyer_request(job: dict) -> bool:
    text = _combined(job)
    if any(marker in text for marker in _BUYER_REQUEST_MARKERS):
        return True

    title = str(job.get("title", ""))
    if _IMPERATIVE_TITLE.search(title) and not any(marker in text for marker in _SELLER_MARKERS):
        return True
    return False


def _seller_evidence(job: dict) -> bool:
    text = _combined(job)
    if any(marker in text for marker in _SELLER_MARKERS):
        return True

    title = str(job.get("title", "")).lower()
    price_range = bool(re.search(r"\$\s*\d+\s*[-–—]\s*\$?\s*\d+", title))
    service_nouns = sum(
        term in title
        for term in (
            "service", "services", "assistant", "agent", "research reports",
            "p&l analysis", "lead generation", "web scraping", "technical writing",
            "code review", "security audit", "automation", "content writing",
        )
    )
    if price_range and service_nouns >= 1 and not _positive_buyer_request(job):
        return True
    return False


def _positive_concrete_scope(job: dict) -> bool:
    text = _combined(job)
    concrete_object = any(pattern.search(text) for pattern in _CONCRETE_OBJECT_PATTERNS)
    structured = any(
        job.get(key)
        for key in ("acceptanceCriteria", "acceptance_criteria", "deliverables", "requirements")
    )
    return concrete_object or bool(structured and _positive_buyer_request(job))


def _score_v3(job: dict, distribution: dict | None = None) -> dict:
    result = _OLD_SCORE(job, distribution)
    flags = list(result.get("risk_flags") or [])

    seller = _seller_evidence(job)
    buyer = _positive_buyer_request(job)
    concrete = _positive_concrete_scope(job)

    if seller:
        result["action"] = "SKIP"
        result["score"] = min(float(result.get("score", 0.0)), -5.0)
        result["acceptance_probability_heuristic"] = 0.0
        result["expected_net_after_10pct_fee"] = 0.0
        result["ev_per_hour"] = 0.0
        if "positive-seller-evidence" not in flags:
            flags.append("positive-seller-evidence")
    elif not buyer:
        if result.get("action") == "QUALIFY":
            result["action"] = "REVIEW"
        if "positive-buyer-proof-missing" not in flags:
            flags.append("positive-buyer-proof-missing")
    elif not concrete:
        if result.get("action") == "QUALIFY":
            result["action"] = "REVIEW"
        if "concrete-task-object-missing" not in flags:
            flags.append("concrete-task-object-missing")

    if float(result.get("budget", 0.0)) < 5.0 and result.get("action") == "QUALIFY":
        result["action"] = "REVIEW"
        if "sub-$5-manual-review" not in flags:
            flags.append("sub-$5-manual-review")

    result["risk_flags"] = flags
    result["buyer_proof"] = buyer
    result["concrete_scope_proof"] = concrete
    result["seller_evidence"] = seller
    return result


ro.score_job = _score_v3
live._strong_buyer_intent = _positive_buyer_request
live._has_concrete_scope = _positive_concrete_scope
live._looks_like_provider_ad = _seller_evidence


def _proposal_v3(opportunity: dict) -> str:
    text = _combined(opportunity.get("job", {}))
    if "vitest" in text or "unit tests" in text or "unit test" in text:
        return (
            "I’ll first inspect the function contract, imports, and existing test setup; then I’ll add a focused Vitest "
            "suite covering normal behavior, boundaries, and error paths with at least 5 cases. I’ll run the suite, fix "
            "test-only issues within scope, and attach a concise ProofWorker evidence check showing the requested criteria "
            "and the final test result. If the supplied function or runtime assumptions are incomplete, I’ll flag that "
            "explicitly rather than invent behavior."
        )
    return _OLD_PROPOSAL(opportunity)


ro.proposal_for = _proposal_v3


def _bid_payload_v3(schema: dict, opportunity: dict, credentials: dict) -> tuple[dict, list[str]]:
    """Map both published-schema fields and current runtime aliases.

    On 2026-09-08 the live Dealwork validator required `proposedAmount` and
    `proposalText` even though the fetched OpenAPI request schema exposed
    `amount` and `message`. These aliases are deterministic equivalents of the
    already-approved bid amount/proposal, so adding them does not broaden scope.
    """
    payload, missing = _OLD_BID_PAYLOAD(schema, opportunity, credentials)
    amount = float(ro.suggested_bid_amount(opportunity))
    proposal = _proposal_v3(opportunity)

    # Keep the path/body job identity explicit and identical.
    payload["jobId"] = str(opportunity["id"])
    # Runtime validator currently expects decimal text rather than a JSON number.
    payload["proposedAmount"] = f"{amount:.2f}"
    payload["proposalText"] = proposal

    # Re-evaluate only requirements from the fetched schema; the runtime aliases
    # above are intentionally additional compatibility fields.
    required = set(schema.get("required", [])) if isinstance(schema, dict) else set()
    missing = sorted(str(name) for name in required if name not in payload)
    return payload, missing


ro.bid_payload_from_schema = _bid_payload_v3


def _self_test_v3() -> int:
    # Isolate inherited v2 tests from v3 monkeypatches. Each layer must prove its
    # own contract rather than accidentally testing against the next layer's rules.
    current_provider = live._looks_like_provider_ad
    current_buyer = live._strong_buyer_intent
    current_scope = live._has_concrete_scope
    current_proposal = ro.proposal_for
    current_payload = ro.bid_payload_from_schema
    try:
        live._looks_like_provider_ad = v2._provider_ad_v2
        live._strong_buyer_intent = v2._buyer_intent_v2
        live._has_concrete_scope = v2._concrete_scope_v2
        ro.proposal_for = _OLD_PROPOSAL
        ro.bid_payload_from_schema = _OLD_BID_PAYLOAD
        _OLD_SELF_TEST()
    finally:
        live._looks_like_provider_ad = current_provider
        live._strong_buyer_intent = current_buyer
        live._has_concrete_scope = current_scope
        ro.proposal_for = current_proposal
        ro.bid_payload_from_schema = current_payload

    corbin = {
        "id": "corbin-service",
        "title": "Financial Operations & P&L Analysis for Solo Operators ($10-$80)",
        "description": (
            "I am Corbin, a transparent AI agent (no human pretense). Financial operations for solo operators.\n"
            "WHAT I DELIVER:\n1. P&L teardown\n2. Profit First setup\n3. Bookkeeping system\n"
            "I work from CSVs, bank statements, and financial data. Deliverables: spreadsheets and analysis. "
            "Typical turnaround 2-8 hours."
        ),
        "fixedPrice": "80",
        "acceptanceCriteria": [
            {"description": "Deliverable matches scope agreed in chat", "verificationMethod": "human_review"}
        ],
    }
    corbin_result = ro.score_job(corbin, None)
    assert corbin_result["action"] == "SKIP", corbin_result
    assert corbin_result["seller_evidence"] is True
    assert corbin_result["buyer_proof"] is False

    buyer = {
        "id": "buyer-real",
        "title": "Fix pagination bug in my repository",
        "description": (
            "I need someone to fix this bug in the provided repository. "
            "Acceptance criteria: tests pass and invalid pages return HTTP 400."
        ),
        "fixedPrice": "30",
        "acceptanceCriteria": ["tests pass", "invalid pages return 400"],
    }
    buyer_result = ro.score_job(buyer, None)
    assert buyer_result["action"] == "QUALIFY", buyer_result
    assert buyer_result["buyer_proof"] is True
    assert buyer_result["concrete_scope_proof"] is True
    assert buyer_result["seller_evidence"] is False

    tiny = {
        "id": "tiny",
        "title": "Write a Python script to process CSV data",
        "description": "Please write a script for this CSV. Deliverable: script plus example output.",
        "fixedPrice": "3",
        "acceptanceCriteria": ["script processes supplied CSV"],
    }
    tiny_result = ro.score_job(tiny, None)
    assert tiny_result["action"] == "REVIEW", tiny_result

    # Reproduce the exact schema/runtime drift observed live: fetched OpenAPI
    # advertises amount/message, while the runtime requires proposedAmount and
    # proposalText. The compatibility mapper must include both sets safely.
    stale_schema = {
        "type": "object",
        "required": ["jobId", "amount", "message"],
        "properties": {
            "jobId": {"type": "string"},
            "amount": {"type": "string"},
            "message": {"type": "string"},
        },
    }
    unit_test_opportunity = {
        "id": "job-vitest-1",
        "title": "Write unit tests for a JavaScript function",
        "budget": 5.0,
        "estimated_hours": 2.0,
        "action": "QUALIFY",
        "risk_flags": ["sandbox-before-untrusted-exec"],
        "job": {
            "title": "Write unit tests for a JavaScript function",
            "description": "Given a JavaScript/TypeScript function, write comprehensive unit tests using Vitest.",
        },
    }
    bid_payload, missing = _bid_payload_v3(stale_schema, unit_test_opportunity, {"agentAccountId": "agent-1"})
    assert not missing, missing
    assert bid_payload["jobId"] == "job-vitest-1"
    assert bid_payload["proposedAmount"] == "5.00"
    assert isinstance(bid_payload["proposedAmount"], str)
    assert "Vitest" in bid_payload["proposalText"]
    assert bid_payload["amount"] == "5.00"
    assert bid_payload["message"] == bid_payload["proposalText"]

    print("LIVE V3 SELF-TEST PASS")
    return 0


ro.self_test = _self_test_v3


if __name__ == "__main__":
    raise SystemExit(ro.main())
