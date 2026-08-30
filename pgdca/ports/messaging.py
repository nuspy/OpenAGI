"""Email and SMS ports (spec §19): tools, not memory.

Messages become structured events; received content is untrusted data.
The tool wrapper (not the adapter) appends the honest-identity footer
to outbound email - the system acts declaredly on behalf of its
principal, never impersonating.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class MessageEvent:
    id: str
    channel: str                    # email | sms
    sender: str
    recipient: str
    body: str
    subject: str = ""
    ts: str = ""
    trust: str = "untrusted"


class EmailPort(Protocol):
    def send(self, to: str, subject: str, body: str) -> str: ...
    def fetch_unread(self) -> list[MessageEvent]: ...


class SmsPort(Protocol):
    def send(self, to: str, body: str) -> str: ...
    def fetch_unread(self) -> list[MessageEvent]: ...


class MockEmailAdapter:
    def __init__(self, inbox: list[MessageEvent] | None = None):
        self.outbox: list[dict] = []
        self._inbox = list(inbox or [])
        self._n = 0

    def send(self, to: str, subject: str, body: str) -> str:
        self._n += 1
        mid = f"mail_{self._n}"
        self.outbox.append({"id": mid, "to": to, "subject": subject, "body": body})
        return mid

    def fetch_unread(self) -> list[MessageEvent]:
        out, self._inbox = self._inbox, []
        return out


class MockSmsAdapter:
    def __init__(self, inbox: list[MessageEvent] | None = None):
        self.outbox: list[dict] = []
        self._inbox = list(inbox or [])
        self._n = 0

    def send(self, to: str, body: str) -> str:
        self._n += 1
        mid = f"sms_{self._n}"
        self.outbox.append({"id": mid, "to": to, "body": body})
        return mid

    def fetch_unread(self) -> list[MessageEvent]:
        out, self._inbox = self._inbox, []
        return out


def conformance_email(port: EmailPort) -> list[str]:
    problems: list[str] = []
    try:
        mid = port.send("probe@example.invalid", "conformance", "probe")
        if not isinstance(mid, str) or not mid:
            problems.append("send must return a message id")
        unread = port.fetch_unread()
        if not isinstance(unread, list):
            problems.append("fetch_unread must return a list")
    except Exception as exc:  # noqa: BLE001
        problems.append(f"lifecycle raised: {exc!r}")
    return problems


def conformance_sms(port: SmsPort) -> list[str]:
    problems: list[str] = []
    try:
        mid = port.send("+000000000", "probe")
        if not isinstance(mid, str) or not mid:
            problems.append("send must return a message id")
        if not isinstance(port.fetch_unread(), list):
            problems.append("fetch_unread must return a list")
    except Exception as exc:  # noqa: BLE001
        problems.append(f"lifecycle raised: {exc!r}")
    return problems
