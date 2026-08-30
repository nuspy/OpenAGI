"""Vault/payments and identity/2FA ports (spec §17-§18).

The ports expose capabilities, never secrets: only opaque handles
(`payment_method_id`, `auth_session_id`, ...) cross the boundary. Raw
credentials and 2FA codes never enter LLM context or the event log.
Payment flows assume strong customer authentication - human-in-the-loop
above thresholds is the normal case.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class PaymentResult:
    tx_id: str
    status: str                 # completed | pending_sca | failed
    amount: float = 0.0
    currency: str = "EUR"
    metadata: dict = field(default_factory=dict)


class VaultPort(Protocol):
    def payment_methods(self) -> list[dict]: ...
    def pay(self, method_handle: str, merchant: str, amount: float,
            currency: str, purpose: str, authorization_context: str) -> PaymentResult: ...


class IdentityPort(Protocol):
    def auth_session(self, service_handle: str) -> dict: ...
    def request_2fa(self, channel_handle: str) -> dict: ...


class MockVaultAdapter:
    def __init__(self):
        self.transactions: list[dict] = []
        self._n = 0

    def payment_methods(self) -> list[dict]:
        return [{"handle": "pm_mock_1", "label": "Mock card ***1111",
                 "kind": "card"}]

    def pay(self, method_handle: str, merchant: str, amount: float,
            currency: str, purpose: str, authorization_context: str) -> PaymentResult:
        self._n += 1
        tx = {"tx_id": f"tx_{self._n}", "method": method_handle,
              "merchant": merchant, "amount": amount, "currency": currency,
              "purpose": purpose, "authorization_context": authorization_context}
        self.transactions.append(tx)
        return PaymentResult(tx_id=tx["tx_id"], status="completed",
                             amount=amount, currency=currency)


class MockIdentityAdapter:
    def auth_session(self, service_handle: str) -> dict:
        return {"session_handle": f"sess_{service_handle}", "expires_s": 900}

    def request_2fa(self, channel_handle: str) -> dict:
        # the code goes to the human's device, never through this port
        return {"challenge_id": f"chal_{channel_handle}", "delivered": True}


def conformance_vault(port: VaultPort) -> list[str]:
    problems: list[str] = []
    try:
        methods = port.payment_methods()
        if not isinstance(methods, list):
            problems.append("payment_methods must return a list of handle dicts")
        for m in methods:
            for k, v in m.items():
                if isinstance(v, str) and sum(c.isdigit() for c in v) >= 13:
                    problems.append(f"method field '{k}' looks like a raw PAN - "
                                    "handles only, never credentials")
    except Exception as exc:  # noqa: BLE001
        problems.append(f"payment_methods raised: {exc!r}")
    return problems


def conformance_identity(port: IdentityPort) -> list[str]:
    problems: list[str] = []
    try:
        s = port.auth_session("svc_probe")
        if "session_handle" not in s:
            problems.append("auth_session must return a session_handle")
        c = port.request_2fa("chan_probe")
        if "code" in c:
            problems.append("request_2fa must never return the code itself")
    except Exception as exc:  # noqa: BLE001
        problems.append(f"lifecycle raised: {exc!r}")
    return problems
