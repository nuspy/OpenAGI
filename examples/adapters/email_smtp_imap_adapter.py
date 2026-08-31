"""Real email adapter behind EmailPort: plain SMTP (send) + IMAP (fetch).

Works with any standard mailbox; for Gmail create an app password
(Google Account -> Security -> 2-Step Verification -> App passwords)
and use it as PGDCA_EMAIL_PASSWORD - never the account password.

Configuration (env vars; credentials never live in this repo):

    PGDCA_EMAIL_ADDRESS    the mailbox (e.g. name@gmail.com)  [required]
    PGDCA_EMAIL_PASSWORD   app password / SMTP password       [required]
    PGDCA_SMTP_HOST        default smtp.gmail.com
    PGDCA_SMTP_PORT        default 587 (STARTTLS)
    PGDCA_IMAP_HOST        default imap.gmail.com
    PGDCA_IMAP_PORT        default 993 (SSL)

Design points (the architecture's doctrine, not niceties):
- the honest-identity footer is appended by the `email.send` wrapper in
  pgdca/tools/external.py, NOT here - no adapter can skip it;
- fetched messages come back as MessageEvent with trust="untrusted":
  their content is data, never instructions;
- fetch_unread marks messages as read (Seen) so the same input is not
  woven twice into the loop.

The port conformance suite SENDS a real probe email: run it manually,
to yourself (docs/LOCAL_INTEGRATIONS.md). Automated tests use fakes.
"""
from __future__ import annotations

import email as email_lib
import os
from email.header import decode_header, make_header
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid

from pgdca.ports.messaging import MessageEvent


def _decode(value: str | None) -> str:
    try:
        return str(make_header(decode_header(value or "")))
    except Exception:  # noqa: BLE001 - malformed headers are attacker input
        return value or ""


def _body_text(msg) -> str:
    """Plain-text body, first 20000 chars; HTML-only mails fall back raw."""
    parts = msg.walk() if msg.is_multipart() else [msg]
    fallback = ""
    for p in parts:
        if p.get_content_maintype() != "text":
            continue
        try:
            text = p.get_payload(decode=True).decode(
                p.get_content_charset() or "utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            continue
        if p.get_content_subtype() == "plain":
            return text[:20000]
        fallback = fallback or text
    return fallback[:20000]


class SmtpImapEmailAdapter:
    def __init__(self, address: str | None = None, password: str | None = None,
                 smtp_host: str | None = None, smtp_port: int | None = None,
                 imap_host: str | None = None, imap_port: int | None = None,
                 smtp_factory=None, imap_factory=None):
        self.address = address or os.environ.get("PGDCA_EMAIL_ADDRESS", "")
        self.password = password if password is not None else \
            os.environ.get("PGDCA_EMAIL_PASSWORD", "")
        if not self.address or not self.password:
            raise RuntimeError(
                "email adapter not configured: set PGDCA_EMAIL_ADDRESS and "
                "PGDCA_EMAIL_PASSWORD (for Gmail, an app password)")
        self.smtp_host = smtp_host or os.environ.get("PGDCA_SMTP_HOST",
                                                     "smtp.gmail.com")
        self.smtp_port = int(smtp_port or os.environ.get("PGDCA_SMTP_PORT",
                                                         587))
        self.imap_host = imap_host or os.environ.get("PGDCA_IMAP_HOST",
                                                     "imap.gmail.com")
        self.imap_port = int(imap_port or os.environ.get("PGDCA_IMAP_PORT",
                                                         993))
        # injectable for tests: no network in the automated suite
        if smtp_factory is None:
            import smtplib

            def smtp_factory():
                s = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)
                s.starttls()
                return s
        if imap_factory is None:
            import imaplib

            def imap_factory():
                return imaplib.IMAP4_SSL(self.imap_host, self.imap_port,
                                         timeout=30)
        self._smtp_factory = smtp_factory
        self._imap_factory = imap_factory

    # ------------------------------------------------------------ EmailPort

    def send(self, to: str, subject: str, body: str) -> str:
        msg = MIMEText(body, "plain", "utf-8")
        msg["From"] = self.address
        msg["To"] = to
        msg["Subject"] = subject
        msg["Date"] = formatdate(localtime=True)
        mid = make_msgid()
        msg["Message-ID"] = mid
        smtp = self._smtp_factory()
        try:
            smtp.login(self.address, self.password)
            smtp.sendmail(self.address, [to], msg.as_string())
        finally:
            try:
                smtp.quit()
            except Exception:  # noqa: BLE001
                pass
        return mid

    def fetch_unread(self) -> list[MessageEvent]:
        imap = self._imap_factory()
        out: list[MessageEvent] = []
        try:
            imap.login(self.address, self.password)
            imap.select("INBOX")
            status, data = imap.search(None, "UNSEEN")
            if status != "OK":
                return []
            for num in (data[0].split() if data and data[0] else []):
                status, fetched = imap.fetch(num, "(RFC822)")
                if status != "OK" or not fetched or fetched[0] is None:
                    continue
                msg = email_lib.message_from_bytes(fetched[0][1])
                out.append(MessageEvent(
                    id=_decode(msg.get("Message-ID")) or num.decode(),
                    channel="email",
                    sender=_decode(msg.get("From")),
                    recipient=_decode(msg.get("To")) or self.address,
                    subject=_decode(msg.get("Subject")),
                    body=_body_text(msg),
                    ts=_decode(msg.get("Date")),
                    trust="untrusted"))
                # already-woven input must not come back next cycle
                imap.store(num, "+FLAGS", "\\Seen")
        finally:
            try:
                imap.logout()
            except Exception:  # noqa: BLE001
                pass
        return out
