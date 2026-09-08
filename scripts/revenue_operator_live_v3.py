#!/usr/bin/env python3
"""ProofWorker live revenue guard v3.

Default-deny live bidding: a Dealwork post may QUALIFY only when there is
positive evidence of buyer intent for a concrete task. Structured acceptance
criteria alone are not buyer evidence because supply-side service ads may carry
them too.
"""
from __future__ import annotations

import re

import revenue_operator_live_v2 as v2

live = v2.live
ro = live.ro

_OLD_SELF_TEST = ro.self_test
_OLD_SCORE = ro.score_job


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

_CONCRETE_OBJECT_MARKERS = (
    "repository",
    "repo",
    "github",
    "codebase",
    "existing app",
    "existing code",
    "api endpoint",
    "this api",
    "this file",
    "provided file",
    "attached file",
    "dataset",
    "this dataset",
    "provided data",
    "csv",
    "spreadsheet",
    "document",
    "url",
    "issue #",
    "bug",
    "fixture",
    "test suite",
)

_IMPERATIVE_TITLE = re.compile(
    r"^\s*(fix|build|create|write|review|audit|analy[sz]e|update|implement|debug|"
    r"generate|convert|clean|refactor|migrate|document)\b",
    re.IGNORECASE,
)


def _combined(job: dict) -> str:
    return f"{job.get('title', '')} {job.get('description', '')}".lower()


def _seller_evidence(job: dict) -> bool:
    text = _combined(job)
    hits = sum(marker in text for marker in _SELLER_MARKERS)
    if hits >= 1:
        return True

    title = str(job.get("title", "")).lower()
    # Menu-style productized work with a price range is supply unless the body
    # contains a direct buyer request.
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


def _positive_buyer_request(job: dict) -> bool:
    text = _combined(job)
    if any(marker in text for marker in _BUYER_REQUEST_MARKERS):
        return True

    # Imperative task titles are useful weak-positive evidence, but only when the
    # body does not describe the poster's own service catalogue.
    title = str(job.get("title", ""))
    if _IMPERATIVE_TITLE.search(title) and not any(marker in text for marker in _SELLER_MARKERS):
        return True
    return False


def _positive_concrete_scope(job: dict) -> bool:
    text = f" {_combined(job)} "
    concrete_object = any(marker in text for marker in _CONCRETE_OBJECT_MARKERS)
    structured = any(
        job.get(key)
        for key in ("acceptanceCriteria", "acceptance_criteria", "deliverables", "requirements")
    )
    # Structured criteria are supporting evidence only; they cannot create buyer
    # intent on their own.
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

    # Never live-bid a tiny task merely because it is easy; keep sub-$5 work for
    # manual review/reputation experiments.
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

# v1/v2 evidence preview resolves these module globals. Patch them so the A3
# preview displays the same positive-proof policy as ranking.
live._strong_buyer_intent = _positive_buyer_request
live._has_concrete_scope = _positive_concrete_scope
live._looks_like_provider_ad = _seller_evidence


def _self_test_v3() -> int:
    _OLD_SELF_TEST()

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

    print("LIVE V3 SELF-TEST PASS")
    return 0


ro.self_test = _self_test_v3


if __name__ == "__main__":
    raise SystemExit(ro.main())
