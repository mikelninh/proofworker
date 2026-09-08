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


def _has_explicit_buyer_scope(job: dict) -> bool:
    if any(job.get(key) for key in ("acceptanceCriteria", "acceptance_criteria", "deliverables", "requirements")):
        return True
    text = " ".join(str(job.get(key, "")) for key in ("title", "description")).lower()
    return "acceptance criteria" in text or "deliverable" in text or "requirements" in text


def _looks_like_provider_ad(job: dict) -> bool:
    title = str(job.get("title", "")).lower()
    description = str(job.get("description", "")).lower()
    combined = f"{title} {description}"

    service_terms = sum(
        term in title
        for term in (
            "code review", "research", "technical writing", "data analysis",
            "automation", "api integration", "full-stack", "security testing",
            "web scraping", "content writing", "python dev", "bug fixes",
        )
    )
    agent_brand = any(
        term in title
        for term in (
            "agent —", "agent -", "assistant —", "assistant -", "grok",
            "hermesworkagent", "birbus", "arena-solver", "marvis", "zapia",
            "solo dev agent", "cherry —",
        )
    )
    price_range_in_title = bool(re.search(r"\$\s*\d+\s*[-–—]\s*\$?\s*\d+", title))
    explicit_offer_language = any(
        phrase in combined
        for phrase in (
            "available for", "we offer", "i offer", "hire me", "service offering",
            "services include", "service includes", "i can help with",
        )
    )

    if explicit_offer_language and service_terms >= 2:
        return True
    if agent_brand and price_range_in_title and service_terms >= 2:
        return True
    if price_range_in_title and service_terms >= 3 and not _has_explicit_buyer_scope(job):
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
        # It stays visible for review rather than being silently discarded.
        if result.get("action") == "QUALIFY":
            result["action"] = "REVIEW"
            result["score"] = round(float(result["score"]) - 8.0, 2)
            flags = list(result.get("risk_flags") or [])
            flags.append("acceptance-criteria-not-explicit")
            result["risk_flags"] = flags
    return result


ro.score_job = _score_job_live


_ORIGINAL_SUGGESTED_BID = ro.suggested_bid_amount


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


if __name__ == "__main__":
    raise SystemExit(ro.main())
