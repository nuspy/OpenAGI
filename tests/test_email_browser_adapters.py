"""Real email (SMTP/IMAP) and browser (Playwright) adapters - fakes only.

The email conformance suite sends real mail and the browser drives a real
Chromium: both stay manual. Here the transports are injected fakes.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from examples.adapters.email_smtp_imap_adapter import SmtpImapEmailAdapter  # noqa: E402
from examples.adapters.playwright_browser_adapter import detect_challenge  # noqa: E402
from pgdca.ports import messaging  # noqa: E402
from pgdca.tools.external import register_external_ports  # noqa: E402
from pgdca.tools.registry import ToolRegistry  # noqa: E402

RAW_MAIL = (b"From: Mario <mario@example.test>\r\n"
            b"To: me@example.test\r\nSubject: Offerta scarponi\r\n"
            b"Date: Mon, 31 Aug 2026 10:00:00 +0200\r\n"
            b"Message-ID: <m1@example.test>\r\n"
            b"Content-Type: text/plain; charset=utf-8\r\n\r\n"
            b"Prezzo 120 EUR, consegna 2 giorni.")


class FakeSmtp:
    sent: list = []

    def login(self, user, pwd):
        self.creds = (user, pwd)

    def sendmail(self, frm, to, data):
        FakeSmtp.sent.append({"from": frm, "to": to, "data": data})

    def quit(self):
        pass


class FakeImap:
    def __init__(self):
        self.flags: list = []

    def login(self, user, pwd):
        pass

    def select(self, box):
        pass

    def search(self, charset, criteria):
        assert criteria == "UNSEEN"
        return "OK", [b"1"]

    def fetch(self, num, what):
        return "OK", [(b"1 (RFC822)", RAW_MAIL)]

    def store(self, num, op, flag):
        self.flags.append((num, op, flag))

    def logout(self):
        pass


def make_adapter(imap=None):
    return SmtpImapEmailAdapter(
        address="me@example.test", password="app-pass",
        smtp_factory=lambda: FakeSmtp(),
        imap_factory=lambda: imap or FakeImap())


def test_send_builds_rfc822_and_returns_message_id():
    FakeSmtp.sent = []
    mid = make_adapter().send("dest@example.test", "Ciao", "corpo")
    assert mid.startswith("<") and FakeSmtp.sent
    data = FakeSmtp.sent[0]["data"]
    assert "Subject: Ciao" in data and FakeSmtp.sent[0]["to"] == ["dest@example.test"]


def test_fetch_unread_returns_untrusted_events_and_marks_seen():
    imap = FakeImap()
    events = make_adapter(imap).fetch_unread()
    assert len(events) == 1
    ev = events[0]
    assert ev.trust == "untrusted" and ev.channel == "email"
    assert "120 EUR" in ev.body and ev.subject == "Offerta scarponi"
    assert imap.flags and imap.flags[0][2] == "\\Seen"


def test_unconfigured_adapter_fails_with_clear_message(monkeypatch):
    monkeypatch.delenv("PGDCA_EMAIL_ADDRESS", raising=False)
    monkeypatch.delenv("PGDCA_EMAIL_PASSWORD", raising=False)
    with pytest.raises(RuntimeError, match="PGDCA_EMAIL_ADDRESS"):
        SmtpImapEmailAdapter()


def test_wrapper_appends_identity_footer_over_real_adapter():
    FakeSmtp.sent = []
    reg = ToolRegistry()
    register_external_ports(reg, email=make_adapter(), principal="Andrea")
    r = reg.execute("email.send", {"to": "x@example.test", "subject": "hi",
                                   "body": "contenuto"})
    assert r.status == "ok"
    import email as email_lib
    sent = email_lib.message_from_string(FakeSmtp.sent[0]["data"])
    body = sent.get_payload(decode=True).decode("utf-8")
    assert "on behalf of Andrea" in body


def test_port_conformance_over_fakes():
    assert messaging.conformance_email(make_adapter()) == []


def test_challenge_detection_heuristic():
    assert detect_challenge("Just a moment...", "Checking your browser") is not None
    assert detect_challenge("Attention Required! | Cloudflare", "") is not None
    assert detect_challenge("Shop", "Scarponi da montagna 120 EUR") is None
