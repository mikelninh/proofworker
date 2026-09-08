#!/usr/bin/env python3
"""ProofWorker live revenue guard v5.

Prioritizes Dealwork's authenticated matching feed and applies an economic gate
before open-mode claims. Public feed remains a fallback. Claim-mode work is not
allowed to QUALIFY when the worker wallet is empty, the commitment is unknown,
or the wallet cannot cover the explicit commitment.
"""
from __future__ import annotations

from typing import Any

import revenue_operator_live_v4 as v4

ro = v4.ro

_OLD_RANKED = ro.ranked_jobs
_OLD_SELF_TEST = ro.self_test


def _matching_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data", payload)
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("matches", "jobs", "items", "results"):
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def _unwrap_job(item: dict[str, Any]) -> dict[str, Any]:
    nested = item.get("job")
    return nested if isinstance(nested, dict) else item


def _wallet_available(balance: dict[str, Any]) -> float | None:
    if not isinstance(balance, dict) or "unavailable" in balance:
        return None
    for key in ("available", "availableBalance", "balance"):
        value = balance.get(key)
        if value is None:
            continue
        try:
            return max(0.0, float(value))
        except (TypeError, ValueError):
            continue
    return None


def _apply_economic_gate(result: dict[str, Any], wallet_available: float | None) -> dict[str, Any]:
    job = result.get("job") if isinstance(result.get("job"), dict) else {}
    flags = list(result.get("risk_flags") or [])

    if not v4._is_claim_mode(job):
        result["job_mode"] = "bid-or-unknown"
        result["wallet_available"] = wallet_available
        return result

    result["job_mode"] = "claim"
    result["wallet_available"] = wallet_available
    commitment, source = v4._explicit_commitment(job)
    result["claim_commitment"] = commitment
    result["claim_commitment_source"] = source

    blocked = False
    if commitment is None:
        flags.append("claim-commitment-unknown")
        blocked = True
    if wallet_available is None:
        flags.append("claim-wallet-unavailable")
        blocked = True
    elif wallet_available <= 0:
        flags.append("claim-wallet-empty")
        blocked = True
    elif commitment is not None and float(commitment) > wallet_available:
        flags.append("claim-wallet-insufficient")
        blocked = True

    if blocked and result.get("action") == "QUALIFY":
        result["action"] = "REVIEW"
        result["score"] = round(float(result.get("score", 0.0)) - 30.0, 2)

    result["risk_flags"] = list(dict.fromkeys(flags))
    return result


def _score_detail(base_url: str, raw_job: dict[str, Any], wallet_available: float | None) -> dict[str, Any]:
    job_id = str(raw_job.get("id") or raw_job.get("jobId") or "")
    detail = raw_job
    distribution: dict[str, Any] | None = None

    if job_id:
        try:
            detail_payload = ro.request_json(base_url, "GET", f"jobs/{job_id}", timeout=12)
            candidate = ro.data_object(detail_payload)
            if candidate:
                detail = candidate
        except RuntimeError:
            pass
        try:
            distribution = ro.request_json(base_url, "GET", f"jobs/{job_id}/bids/distribution", timeout=12)
        except RuntimeError:
            distribution = None

    scored = ro.score_job(detail, distribution)
    return _apply_economic_gate(scored, wallet_available)


def _ranked_jobs_v5(base_url: str, *, include_microtasks: bool = True, max_pages: int = 3) -> list[dict[str, Any]]:
    creds = ro.read_credentials()
    if not creds:
        return _OLD_RANKED(base_url, include_microtasks=include_microtasks, max_pages=max_pages)

    wallet = v4._wallet_balance(base_url, creds)
    available = _wallet_available(wallet)

    jobs: list[dict[str, Any]] = []
    source = "matching"
    try:
        payload = ro.request_json(
            base_url,
            "GET",
            "jobs/matching",
            bearer=str(creds["apiKey"]),
            timeout=20,
        )
        jobs = [_unwrap_job(item) for item in _matching_items(payload)]
    except RuntimeError as exc:
        print(f"Matching feed unavailable; falling back to public feed: {exc}")

    if not jobs:
        source = "public-fallback"
        fallback = _OLD_RANKED(base_url, include_microtasks=include_microtasks, max_pages=max_pages)
        for item in fallback:
            gated = _apply_economic_gate(item, available)
            gated["discovery_source"] = source
        fallback.sort(
            key=lambda item: (
                1 if item.get("action") == "QUALIFY" else 0,
                1 if item.get("job_mode") != "claim" else 0,
                float(item.get("score", 0.0)),
            ),
            reverse=True,
        )
        return fallback

    seen: set[str] = set()
    scored: list[dict[str, Any]] = []
    for job in jobs:
        job_id = str(job.get("id") or job.get("jobId") or "")
        if job_id and job_id in seen:
            continue
        if job_id:
            seen.add(job_id)
        result = _score_detail(base_url, job, available)
        result["discovery_source"] = source
        scored.append(result)

    scored.sort(
        key=lambda item: (
            1 if item.get("action") == "QUALIFY" else 0,
            1 if item.get("job_mode") != "claim" else 0,
            float(item.get("score", 0.0)),
        ),
        reverse=True,
    )
    return scored


ro.ranked_jobs = _ranked_jobs_v5


def _self_test_v5() -> int:
    _OLD_SELF_TEST()

    payload = {"data": {"matches": [{"job": {"id": "a"}}, {"id": "b"}]}}
    items = _matching_items(payload)
    assert len(items) == 2
    assert _unwrap_job(items[0])["id"] == "a"
    assert _unwrap_job(items[1])["id"] == "b"

    assert _wallet_available({"available": "0.0000"}) == 0.0
    assert _wallet_available({"available": "2.50"}) == 2.5
    assert _wallet_available({"unavailable": "offline"}) is None

    claim = {
        "id": "claim-1",
        "title": "Write tests",
        "fixedPrice": "5",
        "applicationMode": "open",
        "acceptanceCriteria": ["tests pass"],
    }
    base_result = ro.score_job(claim, None)
    base_result["action"] = "QUALIFY"
    empty = _apply_economic_gate(dict(base_result), 0.0)
    assert empty["action"] == "REVIEW", empty
    assert "claim-wallet-empty" in empty["risk_flags"]
    assert "claim-commitment-unknown" in empty["risk_flags"]

    funded_job = dict(claim)
    funded_job["claimCommitmentAmount"] = "1.25"
    funded_result = ro.score_job(funded_job, None)
    funded_result["action"] = "QUALIFY"
    funded = _apply_economic_gate(funded_result, 5.0)
    assert funded["action"] == "QUALIFY", funded
    assert funded["claim_commitment"] == "1.25"

    print("LIVE V5 SELF-TEST PASS")
    return 0


ro.self_test = _self_test_v5


if __name__ == "__main__":
    raise SystemExit(ro.main())
