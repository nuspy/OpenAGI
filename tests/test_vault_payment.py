"""Real payment adapter: authorization gate, 2FA/SCA step, no secret leak.

Owner's flow: "se do l'autorizzazione può pagare; al massimo mi chiede
il codice 2FA". The sandbox provider moves no money.
"""
from __future__ import annotations

from examples.adapters.vault_payment_adapter import (
    SandboxPaymentProvider,
    VaultPaymentAdapter,
)
from pgdca.ports import vault as vault_port
from pgdca.tools.external import register_external_ports
from pgdca.tools.registry import ToolRegistry


def make(sca_over=0.0):
    return VaultPaymentAdapter(
        provider=SandboxPaymentProvider(sca_over=sca_over, code="424242"),
        methods=[{"handle": "pm_visa", "label": "Visa ***4242", "kind": "card"}])


def test_no_authorization_no_charge():
    r = make().pay("pm_visa", "AlpineShop", 320.0, "EUR", "boots", "")
    assert r.status == "failed" and r.metadata["reason"] == "no authorization"


def test_small_amount_completes_without_2fa():
    r = make(sca_over=1000).pay("pm_visa", "Shop", 80.0, "EUR", "socks",
                                "ver_1")
    assert r.status == "completed" and r.tx_id


def test_large_amount_asks_for_2fa_then_completes_with_the_code():
    v = make(sca_over=300)
    r = v.pay("pm_visa", "AlpineShop", 320.0, "EUR", "boots", "ver_1")
    assert r.status == "pending_sca"
    cid = r.metadata["challenge_id"]
    assert cid in v.pending_sca
    # wrong code is refused
    assert v.confirm_sca(cid, "000000").status == "failed"
    # right code completes; the challenge is cleared
    ok = v.confirm_sca(cid, "424242")
    assert ok.status == "completed" and cid not in v.pending_sca


def test_pending_metadata_never_carries_the_code():
    v = make(sca_over=0)
    v.pay("pm_visa", "Shop", 500.0, "EUR", "gear", "ver_1")
    for c in v.pending_sca.values():
        assert "code" not in c and "424242" not in str(c)


def test_methods_expose_no_raw_pan():
    assert vault_port.conformance_vault(make()) == []


def test_wrapper_requires_authorization_and_surfaces_sca():
    reg = ToolRegistry()
    register_external_ports(reg, vault=make(sca_over=300))
    # no authorization_context -> refused by the wrapper
    r = reg.execute("vault.pay", {"method_handle": "pm_visa",
                                  "merchant": "Shop", "amount": 320,
                                  "purpose": "boots"})
    assert r.status == "failed" and "authorization" in r.error
    # authorized -> pending_sca is a successful step carrying the challenge
    r = reg.execute("vault.pay", {"method_handle": "pm_visa",
                                  "merchant": "Shop", "amount": 320,
                                  "purpose": "boots",
                                  "authorization_context": "ver_1"})
    assert r.status == "ok"
    assert r.observation["status"] == "pending_sca"
    assert r.observation["challenge_id"]
