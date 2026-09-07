"""Read-only Dealwork adapter.

Authenticated bidding, claiming, wallet, contract and delivery actions are intentionally
not implemented in v0.1. They are A3 consequential actions and require an explicit
human approval gate in ProofWorker's Product Architect OS.
"""
from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://dealwork.ai/api/v1"


def public_jobs(include_microtasks: bool = False, timeout: int = 10) -> list[dict]:
    qs = urlencode({"include_microtasks": str(include_microtasks).lower()})
    req = Request(f"{BASE_URL}/jobs?{qs}", headers={"User-Agent": "ProofWorker/0.1"})
    with urlopen(req, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    data = payload.get("data", payload)
    if isinstance(data, dict):
        for key in ("jobs", "items", "results"):
            if isinstance(data.get(key), list):
                return data[key]
    return data if isinstance(data, list) else []


def verification_fit(job: dict) -> int:
    text = " ".join(str(job.get(k, "")) for k in ("title", "description", "category", "tags")).lower()
    signals = {
        "test": 3, "qa": 4, "verify": 4, "review": 2, "code": 2, "api": 2,
        "research": 2, "citation": 3, "data": 2, "csv": 2, "documentation": 1,
    }
    return sum(weight for word, weight in signals.items() if word in text)
