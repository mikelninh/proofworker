#!/usr/bin/env python3
"""ProofWorker live revenue guard v4.

Adds an explicit open-mode CLAIM path alongside bid-mode jobs. Claims are A3
because Dealwork open-mode claiming can debit a worker commitment from the
worker wallet. ProofWorker therefore refuses to claim unless an exact
commitment amount is visible in machine-readable job data.
"""
from __future__ import annotations

import json
from typing import Any

import revenue_operator_live_v3 as v3

live = v3.live
ro = live.ro

_OLD_SUBMIT = ro.submit_bid
_OLD_SELF_TEST = ro.self_test
_OLD_STATUS = ro.status


_MODE_KEYS = (
    "mode",
    "jobMode",
    "applicationMode",
    "assignmentMode",
    "workerSelectionMode",
    "selectionMode",
)

_COMMITMENT_KEYS = (
    "claimCommitment",
    "claimCommitmentAmount",
    "workerCommitment",
    "workerCommitmentAmount",
    "commitment",
    "commitmentAmount",
    "claimDeposit",
    "claimDepositAmount",
)


def _data_object(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data", payload)
    return data if isinstance(data, dict) else {}


def _job_detail(base_url: str, opportunity: dict[str, Any]) -> dict[str, Any]:
    response = ro.request_json(base_url, "GET", f"jobs/{opportunity['id']}", timeout=15)
    detail = _data_object(response)
    return detail or dict(opportunity.get("job") or {})


def _mode_value(job: dict[str, Any]) -> str:
    for key in _MODE_KEYS:
        value = job.get(key)
        if value is not None:
            return str(value).strip().lower().replace("_", "-")
    return ""


def _is_claim_mode(job: dict[str, Any]) -> bool:
    value = _mode_value(job)
    return value in {"open", "open-mode", "claim", "claim-mode", "instant-claim"}


def _explicit_commitment(job: dict[str, Any]) -> tuple[str | None, str | None]:
    for key in _COMMITMENT_KEYS:
        if key not in job:
            continue
        value = job.get(key)
        if value is None or value == "":
            continue
        try:
            amount = float(value)
        except (TypeError, ValueError):
            continue
        if amount < 0:
            continue
        return f"{amount:.2f}", key
    return None, None


def _claim_schema(base_url: str) -> dict[str, Any]:
    spec = live.fetch_absolute_json(live.derive_openapi_url(base_url))
    path = spec.get("paths", {}).get("/jobs/{id}/claim", {})
    post = path.get("post", {}) if isinstance(path, dict) else {}
    request_body = post.get("requestBody") if isinstance(post, dict) else None
    if not request_body:
        return {"type": "object", "properties": {}, "required": []}
    content = request_body.get("content", {}) if isinstance(request_body, dict) else {}
    app_json = content.get("application/json", {}) if isinstance(content, dict) else {}
    schema = app_json.get("schema", {}) if isinstance(app_json, dict) else {}
    resolved = live.resolve_schema(spec, schema if isinstance(schema, dict) else {})
    return resolved or {"type": "object", "properties": {}, "required": []}


def _claim_payload_from_schema(
    schema: dict[str, Any],
    opportunity: dict[str, Any],
    credentials: dict[str, Any],
    job: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    props = schema.get("properties", {}) if isinstance(schema, dict) else {}
    required = set(schema.get("required", [])) if isinstance(schema, dict) else set()
    if not isinstance(props, dict):
        props = {}

    proposal = ro.proposal_for(opportunity)
    commitment, _source = _explicit_commitment(job)
    payload: dict[str, Any] = {}

    for name, field_schema in props.items():
        key = ro.normalized(str(name))
        field_schema = field_schema if isinstance(field_schema, dict) else {}
        typ = field_schema.get("type")
        value: Any | None = None

        if key == "jobid":
            value = str(opportunity["id"])
        elif key in {"agentid", "agentaccountid", "workerid", "claimantid"}:
            value = credentials.get("agentAccountId")
        elif key in {"proposal", "proposaltext", "message", "note"}:
            value = proposal
        elif key in {
            "commitment", "commitmentamount", "workercommitment", "workercommitmentamount",
            "claimcommitment", "claimcommitmentamount", "deposit", "depositamount",
        } and commitment is not None:
            value = float(commitment) if typ in {"number", "integer"} else commitment

        if value is not None:
            payload[str(name)] = value

    missing = sorted(str(name) for name in required if name not in payload)
    return payload, missing


def _wallet_balance(base_url: str, credentials: dict[str, Any]) -> dict[str, Any]:
    try:
        response = ro.request_json(
            base_url,
            "GET",
            "wallet/balance",
            bearer=str(credentials["apiKey"]),
            timeout=15,
        )
        return _data_object(response)
    except RuntimeError as exc:
        return {"unavailable": str(exc)}


def _claim_open_job(
    base_url: str,
    opportunity: dict[str, Any],
    credentials: dict[str, Any],
    *,
    require_confirmation: bool = True,
    job: dict[str, Any] | None = None,
):
    job = job or _job_detail(base_url, opportunity)
    commitment, commitment_source = _explicit_commitment(job)

    live._print_job_evidence({**opportunity, "job": job})
    print("\nA3 CLAIM PREVIEW")
    print(f"Job: {opportunity['title']}")
    print(f"Job ID: {opportunity['id']}")
    print(f"Budget: ${opportunity['budget']:.2f}")
    print(f"Detected mode: {_mode_value(job) or 'open-mode confirmed by runtime conflict'}")
    print("Wallet:", json.dumps(_wallet_balance(base_url, credentials), ensure_ascii=False)[:500])

    if commitment is None:
        print("Claim commitment: UNKNOWN")
        print("REFUSED: Dealwork open-mode claims can debit a worker commitment, and no exact commitment amount was exposed in the job data.")
        print("No claim was submitted.")
        return None

    print(f"Claim commitment: ${commitment} (source field: {commitment_source})")
    schema = _claim_schema(base_url)
    payload, missing = _claim_payload_from_schema(schema, opportunity, credentials, job)
    if missing:
        print("Claim schema contains required fields ProofWorker will not guess:", ", ".join(missing))
        print("No claim was submitted.")
        return None

    print("Claim payload fields:", ", ".join(sorted(payload)) or "(empty body)")
    if require_confirmation:
        token = f"CLAIM {opportunity['id']} ${commitment}"
        answer = input(f"\nType exactly '{token}' to claim, or press Enter to skip:\n> ").strip()
        if answer != token:
            print("Skipped. No claim submitted.")
            return None

    response = ro.request_json(
        base_url,
        "POST",
        f"jobs/{opportunity['id']}/claim",
        bearer=str(credentials["apiKey"]),
        body=payload,
        timeout=30,
    )
    claim = _data_object(response)
    print("Job claimed.")
    print("Contract ID:", claim.get("contractId") or claim.get("contract_id") or claim.get("id") or "unknown")
    return claim


def _submit_v4(base_url: str, opportunity: dict[str, Any], credentials: dict[str, Any], *, require_confirmation: bool = True):
    if opportunity.get("action") != "QUALIFY":
        return _OLD_SUBMIT(base_url, opportunity, credentials, require_confirmation=require_confirmation)

    try:
        detail = _job_detail(base_url, opportunity)
    except RuntimeError:
        detail = dict(opportunity.get("job") or {})

    if _is_claim_mode(detail):
        return _claim_open_job(
            base_url,
            opportunity,
            credentials,
            require_confirmation=require_confirmation,
            job=detail,
        )

    try:
        return _OLD_SUBMIT(base_url, opportunity, credentials, require_confirmation=require_confirmation)
    except RuntimeError as exc:
        text = str(exc).lower()
        if "409" in text and "use claim endpoint" in text:
            print("\nDealwork confirmed this is an open-mode claim job, not a bid-mode job.")
            return _claim_open_job(
                base_url,
                opportunity,
                credentials,
                require_confirmation=require_confirmation,
                job=detail,
            )
        raise


ro.submit_bid = _submit_v4


def _status_v4(base_url: str) -> int:
    code = _OLD_STATUS(base_url)
    creds = ro.read_credentials()
    if creds:
        print("Wallet balance:", json.dumps(_wallet_balance(base_url, creds), ensure_ascii=False)[:500])
    return code


ro.status = _status_v4


def _self_test_v4() -> int:
    _OLD_SELF_TEST()

    claim_job = {
        "id": "claim-1",
        "title": "Write tests",
        "description": "Please write Vitest tests for this function.",
        "applicationMode": "open",
        "claimCommitmentAmount": "1.25",
        "fixedPrice": "5",
        "acceptanceCriteria": ["5 tests", "tests pass"],
    }
    assert _is_claim_mode(claim_job)
    commitment, source = _explicit_commitment(claim_job)
    assert commitment == "1.25" and source == "claimCommitmentAmount"

    schema = {
        "type": "object",
        "required": ["jobId", "agentId", "proposalText", "commitmentAmount"],
        "properties": {
            "jobId": {"type": "string"},
            "agentId": {"type": "string"},
            "proposalText": {"type": "string"},
            "commitmentAmount": {"type": "string"},
        },
    }
    opportunity = {
        "id": "claim-1",
        "title": "Write tests",
        "budget": 5.0,
        "estimated_hours": 1.0,
        "action": "QUALIFY",
        "risk_flags": [],
        "job": claim_job,
    }
    payload, missing = _claim_payload_from_schema(
        schema,
        opportunity,
        {"agentAccountId": "agent-1"},
        claim_job,
    )
    assert not missing, missing
    assert payload["jobId"] == "claim-1"
    assert payload["agentId"] == "agent-1"
    assert payload["commitmentAmount"] == "1.25"

    unknown = dict(claim_job)
    unknown.pop("claimCommitmentAmount")
    assert _explicit_commitment(unknown) == (None, None)

    print("LIVE V4 SELF-TEST PASS")
    return 0


ro.self_test = _self_test_v4


if __name__ == "__main__":
    raise SystemExit(ro.main())
