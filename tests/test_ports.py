"""External-world ports: conformance, compliance wrappers, gating."""
from __future__ import annotations

from pgdca.ports import browser as browser_port
from pgdca.ports import messaging, vault as vault_port, voice as voice_port
from pgdca.tools.external import register_external_ports
from pgdca.tools.registry import ToolRegistry


def test_all_mock_ports_pass_conformance():
    assert voice_port.conformance(voice_port.MockVoiceAdapter()) == []
    assert messaging.conformance_email(messaging.MockEmailAdapter()) == []
    assert messaging.conformance_sms(messaging.MockSmsAdapter()) == []
    assert browser_port.conformance(browser_port.MockBrowserAdapter()) == []
    assert vault_port.conformance_vault(vault_port.MockVaultAdapter()) == []
    assert vault_port.conformance_identity(vault_port.MockIdentityAdapter()) == []


def test_connection_points_register_disabled_without_local_adapters():
    reg = ToolRegistry()
    report = register_external_ports(reg)
    assert all(v == [] for v in report.values())
    for name in ("voice.call", "email.send", "sms.send", "browser.navigate",
                 "vault.pay", "identity.auth_session"):
        spec = reg.spec(name)
        assert spec.enabled is False
        assert "pending local adapter" in spec.provenance
        r = reg.execute(name, {})
        assert r.status == "failed" and "disabled" in r.error


def test_supplied_adapter_enables_its_tools():
    reg = ToolRegistry()
    mock_voice = voice_port.MockVoiceAdapter()
    register_external_ports(reg, voice=mock_voice)
    assert reg.spec("voice.call").enabled is True
    assert reg.spec("email.send").enabled is False   # still pending


def test_voice_call_speaks_ai_disclosure_first():
    reg = ToolRegistry()
    mock_voice = voice_port.MockVoiceAdapter(replies=["ok"])
    register_external_ports(reg, voice=mock_voice, principal="Alessandro")
    r = reg.execute("voice.call", {"number": "+390000000", "purpose": "demo",
                                   "lines": ["Hello, quick question."]})
    assert r.status == "ok"
    spoken = mock_voice.calls["call_1"]["spoken"]
    assert "AI assistant" in spoken[0] and "Alessandro" in spoken[0]
    assert r.observation["trust"] == "untrusted"


def test_email_send_appends_honest_identity_footer():
    reg = ToolRegistry()
    mock_email = messaging.MockEmailAdapter()
    register_external_ports(reg, email=mock_email, principal="Alessandro")
    r = reg.execute("email.send", {"to": "x@example.test", "subject": "hi",
                                   "body": "content"})
    assert r.status == "ok"
    assert "on behalf of Alessandro" in mock_email.outbox[0]["body"]


def test_browser_challenge_surfaces_as_explicit_state():
    reg = ToolRegistry()
    register_external_ports(reg, browser=browser_port.MockBrowserAdapter())
    r = reg.execute("browser.navigate", {"url": "https://challenge.test/"})
    assert r.status == "ok"
    assert r.observation["challenge_detected"]["type"] == "captcha"
    assert r.observation["trust"] == "untrusted"


def test_vault_pay_requires_authorization_context():
    reg = ToolRegistry()
    mock_vault = vault_port.MockVaultAdapter()
    register_external_ports(reg, vault=mock_vault)
    r = reg.execute("vault.pay", {"method_handle": "pm_mock_1",
                                  "merchant": "shop", "amount": 10})
    assert r.status == "failed" and "authorization_context" in r.error
    r2 = reg.execute("vault.pay", {"method_handle": "pm_mock_1",
                                   "merchant": "shop", "amount": 10,
                                   "authorization_context": "ver_test"})
    assert r2.status == "ok" and mock_vault.transactions[0]["amount"] == 10


def test_identity_never_returns_codes():
    reg = ToolRegistry()
    register_external_ports(reg, identity=vault_port.MockIdentityAdapter())
    r = reg.execute("identity.request_2fa", {"channel_handle": "sms_1"})
    assert r.status == "ok" and "code" not in r.observation
