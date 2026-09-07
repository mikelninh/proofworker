#!/usr/bin/env python3
"""Owner-first Dealwork connection for ProofWorker.

Consequential actions remain explicit:
- connecting/registering requires owner authorization in the browser
- publishing a listing requires --publish-listing plus an interactive confirmation
- bidding, claiming, spending, contract delivery, and escrow actions are not implemented

Credentials are saved only on the local machine and are never printed.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import secrets
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import webbrowser

DEFAULT_BASE_URL = "https://dealwork.ai/api/v1"
LISTING_TITLE = "Independent AI Deliverable Verification — Evidence-Backed QA"


def config_dir() -> Path:
    override = os.environ.get("PROOFWORKER_CONFIG_DIR")
    return Path(override).expanduser() if override else Path.home() / ".proofworker" / "dealwork"


def request_json(base_url: str, method: str, path: str, *, body: dict[str, Any] | None = None,
                 bearer: str | None = None, timeout: int = 30) -> dict[str, Any]:
    raw = None if body is None else json.dumps(body, separators=(",", ":")).encode("utf-8")
    headers = {"Accept": "application/json", "User-Agent": "ProofWorker/0.2-market-test"}
    if raw is not None:
        headers["Content-Type"] = "application/json"
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    req = Request(f"{base_url.rstrip('/')}/{path.lstrip('/')}", data=raw, headers=headers, method=method)
    try:
        with urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        payload = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Dealwork HTTP {exc.code}: {payload[:500]}") from exc
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
        for key in ("items", "jobs", "listings", "results"):
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def safe_write_credentials(path: Path, credentials: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path.parent, 0o700)
    except OSError:
        pass
    tmp = path.with_suffix(".tmp")
    text = json.dumps(credentials, indent=2) + "\n"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)
    os.replace(tmp, path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def load_credentials(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if payload.get("apiKey") and payload.get("agentAccountId"):
        return payload
    return None


def connect(base_url: str, credentials_path: Path) -> dict[str, Any]:
    existing = load_credentials(credentials_path)
    if existing:
        print(f"Already connected. Agent ID: {existing['agentAccountId']}")
        return existing

    token = secrets.token_hex(16)
    connect_response = request_json(base_url, "POST", "agents/connect/link", body={"connectToken": token})
    connection = data_object(connect_response)
    auth_url = connection.get("authUrl")
    if not auth_url:
        raise RuntimeError("Dealwork did not return an owner authorization URL.")

    print("\nOwner authorization required.")
    print("Your browser should open Dealwork now. If it does not, open this URL:\n")
    print(auth_url)
    print()
    webbrowser.open(str(auth_url), new=2)

    authorized = False
    for _ in range(120):
        query = urlencode({"token": token})
        status = request_json(base_url, "GET", f"agents/connect/status?{query}")
        authorized = bool(data_object(status).get("authorized"))
        if authorized:
            break
        time.sleep(3)
    if not authorized:
        raise RuntimeError("Owner authorization timed out. Re-run the command for a fresh link.")

    description = (
        "Independent QA verifier for AI-generated code, research, and structured data. "
        "Checks submitted work against explicit acceptance criteria and returns criterion-level "
        "PASS / FAIL / UNKNOWN with reproducible evidence. Strong at test execution, file/schema "
        "checks, source verification, and failure reporting. Untrusted remote code is never "
        "executed without an approved sandbox."
    )
    onboard = request_json(base_url, "POST", "agents/onboard", body={
        "connectToken": token,
        "agentName": "ProofWorker",
        "description": description,
        "framework": "custom",
        "capabilityTags": ["qa", "testing", "verification", "code-review", "data-analysis"],
    }, timeout=60)
    agent = data_object(onboard)
    if not agent.get("agentAccountId") or not agent.get("apiKey"):
        raise RuntimeError("Dealwork authorized the connection but onboarding did not return agent credentials.")

    credentials = {
        "agentAccountId": agent.get("agentAccountId"),
        "apiKey": agent.get("apiKey"),
        "hmacSecret": agent.get("hmacSecret"),
        "keyPrefix": agent.get("keyPrefix"),
        "ownerAccountId": agent.get("ownerAccountId"),
        "ownerEmail": agent.get("ownerEmail"),
        "baseUrl": "https://dealwork.ai",
    }
    safe_write_credentials(credentials_path, credentials)
    print(f"Connected. Credentials saved locally (not in git): {credentials_path}")
    print(f"Agent ID: {credentials['agentAccountId']}")
    return credentials


def publish_listing(base_url: str, credentials: dict[str, Any], price: str, assume_yes: bool) -> str:
    api_key = str(credentials["apiKey"])
    existing = request_json(base_url, "GET", "listings/mine", bearer=api_key)
    for listing in data_list(existing):
        if listing.get("title") == LISTING_TITLE:
            listing_id = str(listing.get("id") or listing.get("listingId") or "")
            print(f"Launch listing already exists. Listing ID: {listing_id or 'unknown'}")
            return listing_id

    if not assume_yes:
        answer = input(f"Publish ProofWorker launch listing for ${price}? [y/N] ").strip().lower()
        if answer not in {"y", "yes"}:
            print("Listing publication cancelled. Agent connection remains active.")
            return ""

    description = (
        "Send the original task, explicit acceptance criteria, and the AI-generated deliverable. "
        "ProofWorker returns a compact evidence-backed report with PASS / FAIL / UNKNOWN per "
        "criterion, an overall proof score, and reproducible checks. Best for code, research, "
        "JSON/CSV, and document deliverables. No untrusted remote code execution in this launch tier."
    )
    response = request_json(base_url, "POST", "listings", bearer=api_key, body={
        "title": LISTING_TITLE,
        "description": description,
        "category": "development",
        "pricingMode": "fixed",
        "fixedPrice": price,
        "tags": ["qa", "verification", "testing", "ai-agents", "acceptance-criteria"],
        "estimatedDeliveryHours": 2,
    })
    listing = data_object(response)
    listing_id = str(listing.get("id") or listing.get("listingId") or "")
    if not listing_id:
        raise RuntimeError("Dealwork accepted the request but did not return a listing ID.")
    print(f"Launch listing published for ${price}. Listing ID: {listing_id}")
    return listing_id


def verification_fit(job: dict[str, Any]) -> int:
    text = " ".join(str(job.get(key, "")) for key in ("title", "description", "category", "tags")).lower()
    signals = {"qa": 5, "verify": 5, "verification": 5, "test": 4, "acceptance": 4,
               "audit": 3, "review": 3, "code": 2, "api": 2, "research": 2,
               "citation": 3, "data": 2, "csv": 2}
    return sum(weight for word, weight in signals.items() if word in text)


def scan_market(base_url: str) -> None:
    payload = request_json(base_url, "GET", "jobs?per_page=100")
    jobs = data_list(payload)
    ranked = sorted(((verification_fit(job), job) for job in jobs), key=lambda item: item[0], reverse=True)
    print("\nTop verification-fit live jobs:")
    shown = 0
    for score, job in ranked:
        if score <= 0:
            continue
        budget = job.get("fixedPrice") or job.get("budgetMax") or "?"
        print(f"  fit={score:>2}  ${budget}  {job.get('title', '(untitled)')}  [{job.get('id', '?')}]")
        shown += 1
        if shown == 8:
            break
    if shown == 0:
        print("  No verification-fit jobs found in the first 100 public jobs.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Connect ProofWorker to Dealwork with owner-first authorization.")
    parser.add_argument("--publish-listing", action="store_true", help="Publish the launch QA listing after connecting.")
    parser.add_argument("--yes", action="store_true", help="Skip the listing publication confirmation (requires --publish-listing).")
    parser.add_argument("--price", default="5.00", help="Launch listing price in USD (default: 5.00).")
    parser.add_argument("--no-scan", action="store_true", help="Skip the public market scan.")
    parser.add_argument("--base-url", default=os.environ.get("DEALWORK_BASE_URL", DEFAULT_BASE_URL))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        credentials = connect(args.base_url, config_dir() / "credentials.json")
        if args.publish_listing:
            publish_listing(args.base_url, credentials, args.price, args.yes)
        if not args.no_scan:
            scan_market(args.base_url)
        return 0
    except (RuntimeError, KeyboardInterrupt) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
