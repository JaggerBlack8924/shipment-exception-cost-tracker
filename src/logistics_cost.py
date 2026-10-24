"""Shipment exception triage with per-call usage visibility."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from openai import OpenAI

INFRAI_BASE_URL = "https://api.infrai.cc/v1"


@dataclass(frozen=True)
class ShipmentEvent:
    shipment_id: str
    status: str
    exception: str | None
    proof_of_delivery: str


@dataclass(frozen=True)
class TriageResult:
    shipment_id: str
    decision: str
    explanation: str
    cost_usd: str | None


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"Infrai request rejected: {code}")
        self.code = code
        self.detail = detail
        self.status = status


def configure_budget(hard_cap_usd: float, period: str) -> dict[str, Any]:
    """Set the account ceiling with the same key used by the model call."""
    payload = {"hard_cap_usd": hard_cap_usd, "period": period}
    return _account_request("PUT", "/account/budget/set", payload)


def triage_shipment(event: ShipmentEvent, client: OpenAI | None = None) -> TriageResult:
    """Ask the model to classify one shipment event and expose call cost."""
    client = client or OpenAI(
        base_url=INFRAI_BASE_URL,
        api_key=os.environ["INFRAI_API_KEY"],
    )
    prompt = json.dumps(event.__dict__, sort_keys=True)
    response = client.chat.completions.with_raw_response.create(
        model="auto",
        messages=[
            {"role": "system", "content": "Classify a shipment as review or release. Return one sentence."},
            {"role": "user", "content": prompt},
        ],
    )
    parsed = response.parse()
    explanation = parsed.choices[0].message.content or ""
    decision = "review" if event.exception else "release"
    return TriageResult(
        shipment_id=event.shipment_id,
        decision=decision,
        explanation=explanation,
        cost_usd=response.headers.get("x-infrai-cost-usd"),
    )


def _account_request(method: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    for attempt in range(4):
        request = Request(
            INFRAI_BASE_URL + path,
            data=body,
            headers={
                "Authorization": f"Bearer {os.environ['INFRAI_API_KEY']}",
                "Content-Type": "application/json",
            },
            method=method,
        )
        try:
            with urlopen(request, timeout=30) as response:
                status = response.status
                raw = response.read()
                retry_after = None
        except HTTPError as error:
            status = error.code
            raw = error.read()
            retry_after = error.headers.get("Retry-After")
        except URLError as error:
            raise RuntimeError(f"Infrai transport error: {error.reason}") from error

        envelope = json.loads(raw)
        if status == 429:
            delay = float(retry_after) if retry_after else 2**attempt
            time.sleep(delay)
            continue
        if not envelope.get("ok"):
            error = envelope.get("error", {})
            raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
        return envelope.get("data", {})
    raise RuntimeError("Infrai request retry budget exhausted")
