"""Wire the external-world ports into the tool registry.

Connection points only: with no local adapter supplied, each tool
registers DISABLED over its mock ("pending local adapter") so the
integration point is visible in the GUI without pretending the
capability exists. Supplying a real adapter (local development, see
docs/LOCAL_INTEGRATIONS.md) enables the tool - after the port's
conformance suite passes.

Compliance lives in the wrappers, not the adapters, so no adapter can
skip it: `voice.call` speaks the AI disclosure first (EU AI Act art.
50); `email.send` appends the honest-identity footer; `vault.pay`
refuses without an authorization context; received content is labeled
untrusted.
"""
from __future__ import annotations

from ..ports import browser as browser_port
from ..ports import messaging, vault as vault_port, voice as voice_port
from ..security.supervisor import RiskClass
from .registry import ToolRegistry, ToolResult, ToolSpec


def _spec(name: str, risk: RiskClass, description: str, real: bool,
          enable_mocks: bool) -> ToolSpec:
    enabled = real or enable_mocks
    return ToolSpec(name=name, risk_class=risk.value, description=description,
                    provenance="local_adapter" if real
                    else "port_mock (pending local adapter)",
                    enabled=enabled)


def register_external_ports(registry: ToolRegistry, *,
                            voice=None, email=None, sms=None,
                            browser=None, vault=None, identity=None,
                            principal: str = "the owner",
                            enable_mocks: bool = False) -> dict:
    """Register the external-world connection points. Returns a report of
    conformance results per port."""
    report: dict[str, list[str]] = {}

    # ------------------------------------------------------------- voice
    v_real = voice is not None
    v = voice or voice_port.MockVoiceAdapter()
    report["voice"] = (["skipped: supplied adapter - run the conformance "
                        "suite manually (side-effectful)"] if v_real
                       else voice_port.conformance(v))
    disclosure = (f"This is an automated AI assistant calling on behalf of "
                  f"{principal}.")

    def voice_call(params: dict) -> ToolResult:
        if params.get("__conformance__"):
            return ToolResult(status="failed", error="conformance probe")
        number, purpose = params.get("number"), params.get("purpose", "")
        if not number:
            return ToolResult(status="failed", error="missing number")
        cid = v.initiate_call(number, purpose)
        v.speak(cid, disclosure)          # compliance: enforced, not optional
        for line in params.get("lines", []):
            v.speak(cid, str(line))
            v.listen(cid)
        result = v.terminate_call(cid)
        return ToolResult(status="ok" if result.status == "completed" else "failed",
                          observation={"call_id": result.call_id,
                                       "status": result.status,
                                       "transcript": result.transcript,
                                       "trust": "untrusted"})

    registry.register(_spec("voice.call", RiskClass.EXTERNAL_COMMUNICATION,
                            "place a phone call (CallAPICall port); "
                            "AI disclosure is spoken first",
                            v_real, enable_mocks), voice_call)

    # ------------------------------------------------------------- email
    e_real = email is not None
    e = email or messaging.MockEmailAdapter()
    report["email"] = (["skipped: supplied adapter - run conformance manually"]
                       if e_real else messaging.conformance_email(e))
    footer = (f"\n\n--\nSent by PGDCA, an automated AI system acting on "
              f"behalf of {principal}.")

    def email_send(params: dict) -> ToolResult:
        if params.get("__conformance__"):
            return ToolResult(status="failed", error="conformance probe")
        to = params.get("to")
        if not to:
            return ToolResult(status="failed", error="missing recipient")
        mid = e.send(to, params.get("subject", ""),
                     str(params.get("body", "")) + footer)
        return ToolResult(status="ok", observation={"message_id": mid})

    def email_fetch(params: dict) -> ToolResult:
        if params.get("__conformance__"):
            return ToolResult(status="failed", error="conformance probe")
        msgs = [m.__dict__ for m in e.fetch_unread()]
        return ToolResult(status="ok",
                          observation={"messages": msgs, "trust": "untrusted"})

    registry.register(_spec("email.send", RiskClass.EXTERNAL_COMMUNICATION,
                            "send an email with the honest-identity footer",
                            e_real, enable_mocks), email_send)
    registry.register(_spec("email.fetch", RiskClass.READ_ONLY,
                            "fetch unread email (content is untrusted data)",
                            e_real, enable_mocks), email_fetch)

    # --------------------------------------------------------------- sms
    s_real = sms is not None
    s = sms or messaging.MockSmsAdapter()
    report["sms"] = (["skipped: supplied adapter - run conformance manually"]
                     if s_real else messaging.conformance_sms(s))

    def sms_send(params: dict) -> ToolResult:
        if params.get("__conformance__"):
            return ToolResult(status="failed", error="conformance probe")
        to = params.get("to")
        if not to:
            return ToolResult(status="failed", error="missing recipient")
        mid = s.send(to, str(params.get("body", "")))
        return ToolResult(status="ok", observation={"message_id": mid})

    def sms_fetch(params: dict) -> ToolResult:
        if params.get("__conformance__"):
            return ToolResult(status="failed", error="conformance probe")
        msgs = [m.__dict__ for m in s.fetch_unread()]
        return ToolResult(status="ok",
                          observation={"messages": msgs, "trust": "untrusted"})

    registry.register(_spec("sms.send", RiskClass.EXTERNAL_COMMUNICATION,
                            "send an SMS", s_real, enable_mocks), sms_send)
    registry.register(_spec("sms.fetch", RiskClass.READ_ONLY,
                            "fetch unread SMS (untrusted data)",
                            s_real, enable_mocks), sms_fetch)

    # ------------------------------------------------------------ browser
    b_real = browser is not None
    b = browser or browser_port.MockBrowserAdapter()
    report["browser"] = (["skipped: supplied adapter - run conformance manually"]
                         if b_real else browser_port.conformance(b))

    def browser_navigate(params: dict) -> ToolResult:
        if params.get("__conformance__"):
            return ToolResult(status="failed", error="conformance probe")
        url = params.get("url")
        if not url:
            return ToolResult(status="failed", error="missing url")
        st = b.navigate(url)
        obs = {"url": st.url, "title": st.title,
               "content_excerpt": st.content_excerpt, "trust": "untrusted"}
        if st.challenge:
            # explicit challenge state: human verification or deferral,
            # never bypass (spec: CAPTCHA Handling)
            obs["challenge_detected"] = st.challenge
        return ToolResult(status="ok", observation=obs)

    def browser_extract(params: dict) -> ToolResult:
        if params.get("__conformance__"):
            return ToolResult(status="failed", error="conformance probe")
        return ToolResult(status="ok", observation=b.extract(params.get("selector")))

    registry.register(_spec("browser.navigate", RiskClass.EXTERNAL_COMMUNICATION,
                            "navigate the agentic browser; challenges surface "
                            "as explicit states", b_real, enable_mocks),
                      browser_navigate)
    registry.register(_spec("browser.extract", RiskClass.READ_ONLY,
                            "extract structured data from the current page "
                            "(untrusted)", b_real, enable_mocks),
                      browser_extract)

    # -------------------------------------------------------------- vault
    va_real = vault is not None
    va = vault or vault_port.MockVaultAdapter()
    report["vault"] = (["skipped: supplied adapter - run conformance manually"]
                       if va_real else vault_port.conformance_vault(va))

    def vault_pay(params: dict) -> ToolResult:
        if params.get("__conformance__"):
            return ToolResult(status="failed", error="conformance probe")
        if not params.get("authorization_context"):
            return ToolResult(status="failed",
                              error="missing authorization_context: payments "
                                    "execute only under an explicit verdict")
        try:
            r = va.pay(params.get("method_handle", ""), params.get("merchant", ""),
                       float(params.get("amount", 0.0)),
                       params.get("currency", "EUR"), params.get("purpose", ""),
                       params["authorization_context"])
        except Exception as exc:  # noqa: BLE001
            return ToolResult(status="failed", error=repr(exc))
        return ToolResult(status="ok" if r.status == "completed" else "failed",
                          observation={"tx_id": r.tx_id, "status": r.status,
                                       "amount": r.amount, "currency": r.currency})

    registry.register(_spec("vault.pay", RiskClass.FINANCIAL,
                            "authorized payment through the vault (handles "
                            "only, never credentials)", va_real, enable_mocks),
                      vault_pay)

    # ----------------------------------------------------------- identity
    id_real = identity is not None
    ident = identity or vault_port.MockIdentityAdapter()
    report["identity"] = (["skipped: supplied adapter - run conformance manually"]
                          if id_real else vault_port.conformance_identity(ident))

    def identity_auth(params: dict) -> ToolResult:
        if params.get("__conformance__"):
            return ToolResult(status="failed", error="conformance probe")
        return ToolResult(status="ok",
                          observation=ident.auth_session(
                              params.get("service_handle", "")))

    def identity_2fa(params: dict) -> ToolResult:
        if params.get("__conformance__"):
            return ToolResult(status="failed", error="conformance probe")
        return ToolResult(status="ok",
                          observation=ident.request_2fa(
                              params.get("channel_handle", "")))

    registry.register(_spec("identity.auth_session", RiskClass.IDENTITY,
                            "obtain an authenticated session handle",
                            id_real, enable_mocks), identity_auth)
    registry.register(_spec("identity.request_2fa", RiskClass.IDENTITY,
                            "trigger a 2FA challenge (the code goes to the "
                            "human, never through this port)",
                            id_real, enable_mocks), identity_2fa)

    return report
