"""Real payment adapter behind VaultPort, with the SCA (2FA) step.

The owner's ask (2026-08-31): "se do l'autorizzazione può pagare; al
massimo mi chiede il codice 2FA del provider di pagamenti."

How the invariants are kept (spec §17-§18 + the safety doctrine):
- **handles only, never card numbers**: payment methods cross the
  boundary as opaque handles with a last-4 label; no PAN ever enters
  this repo, the LLM context or the event log;
- **your authorization is the gate**: `vault.pay` is FINANCIAL, so the
  Supervisor parks it for your approval; the granted verdict id is the
  `authorization_context` the wrapper passes here - no verdict, no
  charge;
- **the 2FA code stays yours**: when the provider requires Strong
  Customer Authentication the charge returns `pending_sca` with a
  challenge; you type the code into a dedicated endpoint that hands it
  straight to the provider (`confirm_sca`). The code is never stored,
  never logged, never shown to the model - only "SCA confirmed" is
  recorded.

Providers are pluggable. The DEFAULT is a deterministic SANDBOX that
moves no money - safe to run and test. A real provider (Stripe, a bank,
PayPal, ...) is wired locally by you with your own credentials, exactly
like the email/voice adapters; it lives outside this repo.

Configuration (env vars; secrets never in the repo):

    PGDCA_PAY_PROVIDER      "sandbox" (default) | "<your module>:Class"
    PGDCA_PAY_METHODS       JSON list of method handles you expose, e.g.
                            [{"handle":"pm_visa","label":"Visa ***4242",
                              "kind":"card"}]
    PGDCA_PAY_SCA_OVER      amount above which the sandbox asks for 2FA
                            (default 0 = always ask, like real SCA)
    PGDCA_PAY_SANDBOX_CODE  the code the sandbox accepts (default 000000)
"""
from __future__ import annotations

import json
import os

from pgdca.ports.vault import PaymentResult


class SandboxPaymentProvider:
    """Deterministic, offline, moves NO money. Mirrors a real PSP's SCA:
    charges above the threshold come back `pending_sca` and need a code."""

    def __init__(self, sca_over: float = 0.0, code: str = "000000"):
        self.sca_over = sca_over
        self.code = code
        self._n = 0
        self._pending: dict[str, dict] = {}

    def charge(self, method_handle: str, merchant: str, amount: float,
               currency: str, purpose: str) -> dict:
        self._n += 1
        tx = f"sbx_{self._n}"
        if amount > self.sca_over:
            ch = f"sca_{self._n}"
            self._pending[ch] = {"tx_id": tx, "amount": amount,
                                 "currency": currency, "merchant": merchant}
            return {"status": "pending_sca", "tx_id": tx, "challenge_id": ch}
        return {"status": "completed", "tx_id": tx}

    def confirm(self, challenge_id: str, code: str) -> dict:
        ch = self._pending.get(challenge_id)
        if ch is None:
            return {"status": "failed", "reason": "unknown challenge"}
        if code != self.code:
            return {"status": "failed", "reason": "wrong code"}
        self._pending.pop(challenge_id, None)
        return {"status": "completed", "tx_id": ch["tx_id"]}


def _load_provider():
    spec = os.environ.get("PGDCA_PAY_PROVIDER", "sandbox").strip()
    if spec in ("", "sandbox"):
        return SandboxPaymentProvider(
            sca_over=float(os.environ.get("PGDCA_PAY_SCA_OVER", 0) or 0),
            code=os.environ.get("PGDCA_PAY_SANDBOX_CODE", "000000"))
    # "package.module:Class" - your real provider, credentials from its own
    # config/env, outside this repo. It must expose charge()/confirm().
    mod_name, _, cls_name = spec.partition(":")
    import importlib
    cls = getattr(importlib.import_module(mod_name), cls_name)
    return cls()


class VaultPaymentAdapter:
    """`VaultPort` adapter: methods as handles, pay with the SCA step."""

    def __init__(self, provider=None, methods: list | None = None):
        self.provider = provider or _load_provider()
        if methods is None:
            raw = os.environ.get("PGDCA_PAY_METHODS", "").strip()
            methods = json.loads(raw) if raw else [
                {"handle": "pm_sandbox", "label": "Sandbox card ***4242",
                 "kind": "card"}]
        self._methods = methods
        # challenge_id -> public metadata (NO code, NO PAN) for the GUI
        self.pending_sca: dict[str, dict] = {}

    # ------------------------------------------------------------ VaultPort
    def payment_methods(self) -> list[dict]:
        # never expose anything longer than a last-4; conformance checks this
        return [dict(m) for m in self._methods]

    def pay(self, method_handle: str, merchant: str, amount: float,
            currency: str, purpose: str,
            authorization_context: str) -> PaymentResult:
        if not authorization_context:
            # belt-and-braces: the wrapper already refuses, but never charge
            # without an explicit human authorization
            return PaymentResult(tx_id="", status="failed",
                                 amount=amount, currency=currency,
                                 metadata={"reason": "no authorization"})
        r = self.provider.charge(method_handle, merchant, amount, currency,
                                 purpose)
        if r.get("status") == "pending_sca":
            self.pending_sca[r["challenge_id"]] = {
                "challenge_id": r["challenge_id"], "tx_id": r.get("tx_id"),
                "merchant": merchant, "amount": amount, "currency": currency,
                "purpose": purpose, "method": method_handle}
            return PaymentResult(tx_id=r.get("tx_id", ""), status="pending_sca",
                                 amount=amount, currency=currency,
                                 metadata={"challenge_id": r["challenge_id"],
                                           "sca_prompt": "serve il codice di "
                                           "verifica del tuo provider di "
                                           "pagamento"})
        return PaymentResult(tx_id=r.get("tx_id", ""),
                             status=r.get("status", "failed"),
                             amount=amount, currency=currency,
                             metadata={k: v for k, v in r.items()
                                       if k not in ("status", "tx_id")})

    def confirm_sca(self, challenge_id: str, code: str) -> PaymentResult:
        """Hand the human's 2FA code straight to the provider. The code is
        used and dropped here: it is never returned, stored or logged."""
        meta = self.pending_sca.get(challenge_id)
        r = self.provider.confirm(challenge_id, code)
        if r.get("status") == "completed":
            self.pending_sca.pop(challenge_id, None)
        return PaymentResult(
            tx_id=r.get("tx_id", (meta or {}).get("tx_id", "")),
            status=r.get("status", "failed"),
            amount=(meta or {}).get("amount", 0.0),
            currency=(meta or {}).get("currency", "EUR"),
            metadata={"reason": r["reason"]} if r.get("reason") else {})
