#!/usr/bin/env python3
"""Live-safe wrapper for ProofWorker's bounded Dealwork revenue operator.

This wrapper keeps the proven marketplace API base used by the owner-connected
agent, while pinning OpenAPI discovery to Dealwork's current API host and adding
stricter buyer-vs-provider-ad filtering for live bidding.
"""
from __future__ import annotations

import re

import revenue_operator as ro

CURRENT_OPENAPI_URL = "https://api.dealwork.ai/openapi.json"


# Dealwork's current public API docs expose OpenAPI on api.dealwork.ai.
# Keep normal marketplace traffic on the already-proven base URL, but do not
# derive the schema host from it.
def _current_openapi_url(_base_url: str) -> str:
    return CURRENT_OPENAPI_URL


ro.derive_openapi_url = _current_openapi_url


_ORIGINAL_SCORE_JOB = ro.score_job
_ORIGINAL_BID_PAYLOAD = ro.bid_payload_from_schema
_ORIGINAL_SELF_TEST = ro.self_test


_GENERIC_SERVICE_TERMS = (
    "research", "writing", "data", "admin", "code review", "technical writing",
    "data analysis", "automation", "api integration", "full-stack",
    "security testing", "web scraping", "content writing", "python dev",
    "bug fixes", "bilingual", "development service", "assistant",
)

_AGENT_BRANDS = (
    "agent —", "agent -", "assistant —", "assistant -", "grok", "hermesworkagent",
    "birbus", "arena-solver", "marvis", "zapia", "solo dev agent", "cherry —",
    "barney —", "hermes-co",
)

_BUYER_ACTION_TERMS = (
    "fix ", "fix:", "implement ", "add ", "update ", "migrate ", "debug ",
    "investigate ", "review this", "audit this", "analyze this", "analyse this",
    "build ", "create ", "write ", "document this", "convert ", "clean ",
    "need ", "looking for", "help me", "for my ", "our ",
)


def _has_explicit_buyer_scope(job: dict) -> bool:
    if any(job.get(key) for key in ("acceptanceCriteria", "acceptance_criteria", "deliverables", "requirements")):
        return True
    text = " ".join(str(job.get(key, "")) for key in ("title", "description")).lower()
    return "acceptance criteria" in text or "deliverable" in text or "requirements" in text


def _looks_like_provider_ad(job: dict) -> bool:
    title = str(job.get("title", "")).lower()
    description = str(job.get("description", "")).lower()
    combined = f"{title} {description}"

    service_terms = sum(term in title for term in _GENERIC_SERVICE_TERMS)
    agent_brand = any(term in title for term in _AGENT_BRANDS)
    price_range_in_title = bool(re.search(r"\$\s*\d+\s*[-–—]\s*\$?\s*\d+", title))
    explicit_offer_language = any(
        phrase in combined
        for phrase in (
            "available for", "we offer", "i offer", "hire me", "service offering",
            "services include", "service includes", "i can help with", "my services",
            "specialist —", "specialist -", "service —", "service -",
        )
    )
    buyer_action = any(term in combined for term in _BUYER_ACTION_TERMS)

    # Branded agent/assistant + a menu-like price range is almost always another
    # worker advertising itself rather than a buyer asking for a concrete output.
    if agent_brand and price_range_in_title and service_terms >= 1:
        return True
    if explicit_offer_language and service_terms >= 1:
        return True
    if price_range_in_title and service_terms >= 3 and not buyer_action:
        return True

    # Productized generic services such as "P&L Analysis for Solo Operators ($10-$80)"
    # are treated as marketplace supply unless the description clearly asks for
    # work on a specific artifact/problem.
    generic_productized = price_range_in_title and any(
        phrase in title
        for phrase in (
            "for solo operators", "for your niche", "blog posts", "linkedin articles",
            "structured reports", "technical writing", "content writing",
        )
    )
    if generic_productized and not buyer_action:
        return True

    return False


def _score_job_live(job: dict, distribution: dict | None = None) -> dict:
    result = _ORIGINAL_SCORE_JOB(job, distribution)
    if _looks_like_provider_ad(job):
        result["action"] = "SKIP"
        result["score"] = round(float(result["score"]) - 30.0, 2)
        result["acceptance_probability_heuristic"] = min(
            float(result["acceptance_probability_heuristic"]), 0.05
        )
        result["expected_net_after_10pct_fee"] = 0.0
        result["ev_per_hour"] = 0.0
        flags = list(result.get("risk_flags") or [])
        if "provider-advertisement/noise-likely" not in flags:
            flags.append("provider-advertisement/noise-likely")
        result["risk_flags"] = flags
    elif not _has_explicit_buyer_scope(job):
        # A real task can still lack structured criteria, but do not auto-bid it.
        if result.get("action") == "QUALIFY":
            result["action"] = "REVIEW"
            result["score"] = round(float(result["score"]) - 8.0, 2)
            flags = list(result.get("risk_flags") or [])
            if "acceptance-criteria-not-explicit" not in flags:
                flags.append("acceptance-criteria-not-explicit")
            result["risk_flags"] = flags
    return result


ro.score_job = _score_job_live


def _suggested_bid_live(opportunity: dict) -> float:
    budget = float(opportunity["budget"])
    # Early-market reputation phase: competitive without racing to the bottom.
    if budget <= 10:
        factor = 1.0
    elif budget <= 30:
        factor = 0.85
    elif budget <= 80:
        factor = 0.80
    else:
        factor = 0.82
    return round(max(1.0, min(budget, budget * factor)), 2)


ro.suggested_bid_amount = _suggested_bid_live


def _proposal_live(opportunity: dict) -> str:
    job = opportunity["job"]
    title = str(job.get("title", ""))
    text = ro.text_blob(job)

    if "p&l" in text or "financial operations" in text or "profit" in text:
        core = (
            "I can turn the supplied operating numbers into a reconciled P&L view with revenue, costs, "
            "margin and key operating ratios checked against the source inputs. I will flag assumptions, "
            "show the calculations, and return a compact decision-ready summary plus the reconciliation evidence."
        )
    elif "lead generation" in text or "prospect" in text:
        core = (
            "I can build the prospect list against explicit qualification rules, deduplicate it, preserve source URLs, "
            "and include a short evidence field for why each prospect qualifies. I will reconcile requested vs delivered "
            "row counts and flag records that cannot be verified rather than inventing missing data."
        )
    elif "documentation" in text or "openapi" in text or "readme" in text:
        core = (
            "I can produce the requested developer documentation from the supplied code/spec, verify endpoint/function "
            "coverage, include runnable examples and a quickstart, and attach a coverage checklist showing what was "
            "documented and what remains unknown."
        )
    elif "review" in text or "audit" in text or "qa" in text:
        core = (
            "I can run an evidence-first QA pass: reproduce the issue where safe, review the relevant code/API behavior, "
            "return prioritized findings, make a minimal patch when requested, and attach tests/checks that show exactly "
            "what passes, fails, or remains unknown."
        )
    elif "research" in text or "citation" in text:
        core = (
            "I can deliver a sourced research pass with claim-to-source mapping, freshness checks, unsupported-claim "
            "flags, and a concise evidence summary rather than relying on unsupported confidence."
        )
    elif "data" in text or "csv" in text or "json" in text:
        core = (
            "I can deliver this with reconciliation evidence: schema/invariant checks, duplicate/null handling, "
            "before/after counts, and a compact change log so the result is independently checkable."
        )
    else:
        core = (
            "I can execute this against the stated acceptance criteria and return a compact evidence pack showing "
            "exactly what was verified, what failed, and what remains unknown."
        )

    return (
        core
        + " I use ProofWorker as a verification gate before submission, keep scope narrow, and will surface any "
          "required access or unsafe execution step before proceeding."
    )


ro.proposal_for = _proposal_live


def _bid_payload_live(schema: dict, opportunity: dict, credentials: dict) -> tuple[dict, list[str]]:
    """Extend the conservative schema mapper with deterministic job identity.

    Dealwork's current CreateBid schema requires jobId even though the job UUID is
    also present in the URL path. This value is not guessed: it is copied from the
    exact opportunity selected for `/jobs/{id}/bids`.
    """
    payload, _missing = _ORIGINAL_BID_PAYLOAD(schema, opportunity, credentials)
    props = schema.get("properties", {}) if isinstance(schema, dict) else {}
    required = set(schema.get("required", [])) if isinstance(schema, dict) else set()
    if not isinstance(props, dict):
        props = {}

    for name in props:
        key = ro.normalized(str(name))
        if key == "jobid":
            payload[str(name)] = str(opportunity["id"])

    missing = sorted(str(name) for name in required if name not in payload)
    return payload, missing


ro.bid_payload_from_schema = _bid_payload_live


def _self_test_live() -> int:
    _ORIGINAL_SELF_TEST()

    provider_job = {
        "id": "provider-1",
        "title": "Zapia AI Assistant — Research, Writing, Data & Admin ($10-$80)",
        "description": "Research and admin deliverables available with clear requirements.",
        "fixedPrice": "80",
        "requirements": ["research", "writing"],
    }
    provider_result = _score_job_live(provider_job, None)
    assert provider_result["action"] == "SKIP", provider_result

    schema = {
        "type": "object",
        "required": ["jobId", "amount", "proposal"],
        "properties": {
            "jobId": {"type": "string"},
            "amount": {"type": "number"},
            "proposal": {"type": "string"},
        },
    }
    opportunity = {
        "id": "job-123",
        "title": "Fix API pagination bug",
        "budget": 30.0,
        "estimated_hours": 1.25,
        "action": "QUALIFY",
        "risk_flags": [],
        "job": {"title": "Fix API pagination bug", "description": "Fix and add tests"},
    }
    payload, missing = _bid_payload_live(schema, opportunity, {"agentAccountId": "agent-1"})
    assert payload["jobId"] == "job-123", payload
    assert not missing, missing
    print("LIVE SELF-TEST PASS")
    return 0


ro.self_test = _self_test_live


if __name__ == "__main__":
    raise SystemExit(ro.main())
