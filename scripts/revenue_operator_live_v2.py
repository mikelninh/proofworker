#!/usr/bin/env python3
"""ProofWorker live revenue guard v2.

Hardens the v1 live wrapper against supply-side service listings that mimic
buyer jobs by attaching generic acceptance criteria.
"""
from __future__ import annotations

import revenue_operator_live as live

ro = live.ro

_OLD_PROVIDER_AD = live._looks_like_provider_ad
_OLD_BUYER_INTENT = live._strong_buyer_intent
_OLD_CONCRETE_SCOPE = live._has_concrete_scope
_OLD_SELF_TEST = ro.self_test


_PROVIDER_DESCRIPTION_MARKERS = (
    "professional ai agent for",
    "autonomous ai agent",
    "open for work",
    "ready to take orders",
    "available for work",
    "pricing (",
    "pricing:",
    "usdc via escrow",
    "turnaround:",
    "[svc:",
    "small task (",
    "medium (",
    "large (",
    "services include",
    "service includes",
    "my services",
)

_GENERIC_ACCEPTANCE_PHRASES = (
    "deliverable meets stated requirements",
    "report includes methodology notes for verification",
    "human_review",
)


def _text(job: dict) -> str:
    return " ".join(str(job.get(key, "")) for key in ("title", "description")).lower()


def _semantic_provider_ad(job: dict) -> bool:
    text = _text(job)
    marker_hits = sum(marker in text for marker in _PROVIDER_DESCRIPTION_MARKERS)

    # Strong supply-side signature: pricing/turnaround/service identity in the body.
    if marker_hits >= 2:
        return True
    if "professional ai agent" in text and ("pricing" in text or "turnaround" in text):
        return True
    if "usdc via escrow" in text and ("small task" in text or "medium" in text or "large" in text):
        return True

    # Some sellers attach generic acceptance criteria so they resemble buyer jobs.
    # Treat those as non-evidence when paired with any service-side marker.
    criteria = job.get("acceptanceCriteria") or job.get("acceptance_criteria") or []
    criteria_text = str(criteria).lower()
    generic_criteria = any(phrase in criteria_text for phrase in _GENERIC_ACCEPTANCE_PHRASES)
    if marker_hits >= 1 and generic_criteria:
        return True

    return False


def _provider_ad_v2(job: dict) -> bool:
    return _semantic_provider_ad(job) or _OLD_PROVIDER_AD(job)


def _buyer_intent_v2(job: dict) -> bool:
    if _semantic_provider_ad(job):
        return False
    return _OLD_BUYER_INTENT(job)


def _concrete_scope_v2(job: dict) -> bool:
    if _semantic_provider_ad(job):
        return False
    return _OLD_CONCRETE_SCOPE(job)


# The v1 scorer/preview resolves these functions through module globals, so
# replacing them here strengthens both ranking and the A3 evidence preview.
live._looks_like_provider_ad = _provider_ad_v2
live._strong_buyer_intent = _buyer_intent_v2
live._has_concrete_scope = _concrete_scope_v2


def _self_test_v2() -> int:
    _OLD_SELF_TEST()

    hermes_service_ad = {
        "id": "hermes-service",
        "title": "HermesWorkAgent — API Audit, Code Review & Security Testing ($10-80)",
        "description": (
            "Professional AI agent for code review, API auditing, documentation, and security scanning.\n\n"
            "DELIVERABLES:\n- REST API audit\n- Code review\n- Documentation\n\n"
            "PRICING (USDC via escrow):\n- Small task: $10-20\n- Medium: $25-60\n- Large: $60-120\n\n"
            "Turnaround: 1-4 hours. [svc:hermes]"
        ),
        "fixedPrice": "80",
        "acceptanceCriteria": [
            {"description": "Deliverable meets stated requirements.", "verificationMethod": "human_review"},
            {"description": "Report includes methodology notes for verification.", "verificationMethod": "human_review"},
        ],
    }
    result = ro.score_job(hermes_service_ad, None)
    assert result["action"] == "SKIP", result
    assert not live._strong_buyer_intent(hermes_service_ad)
    assert not live._has_concrete_scope(hermes_service_ad)

    real_buyer = {
        "id": "buyer-real",
        "title": "Fix API pagination bug in my repository",
        "description": (
            "I need someone to fix this pagination bug in the provided repository. "
            "Acceptance criteria: tests pass and invalid pages return HTTP 400."
        ),
        "fixedPrice": "30",
        "acceptanceCriteria": ["tests pass", "invalid pages return 400"],
    }
    buyer_result = ro.score_job(real_buyer, None)
    assert buyer_result["action"] == "QUALIFY", buyer_result

    print("LIVE V2 SELF-TEST PASS")
    return 0


ro.self_test = _self_test_v2


if __name__ == "__main__":
    raise SystemExit(ro.main())
