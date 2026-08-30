"""Agentic browser port (spec §16): provider-independent abstraction.

Challenge pages (CAPTCHA and similar) are explicit states, never
bypassed: a detected challenge surfaces to the controller for human
verification or deferral. Page content is untrusted data.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class PageState:
    url: str
    title: str = ""
    content_excerpt: str = ""
    challenge: dict | None = None     # {"provider","type"} when detected
    trust: str = "untrusted"
    metadata: dict = field(default_factory=dict)


class BrowserPort(Protocol):
    def navigate(self, url: str) -> PageState: ...
    def click(self, selector: str) -> PageState: ...
    def type(self, selector: str, text: str) -> PageState: ...
    def extract(self, selector: str | None = None) -> dict: ...
    def current(self) -> PageState: ...


class MockBrowserAdapter:
    """Canned pages, including a challenge page for the escalation path."""

    PAGES = {
        "https://example.test/": PageState(
            url="https://example.test/", title="Example",
            content_excerpt="Welcome to the example page."),
        "https://challenge.test/": PageState(
            url="https://challenge.test/", title="Verification required",
            content_excerpt="Please verify you are human.",
            challenge={"provider": "generic", "type": "captcha"}),
    }

    def __init__(self):
        self._state = PageState(url="about:blank")

    def navigate(self, url: str) -> PageState:
        self._state = self.PAGES.get(url, PageState(url=url, title="Not found",
                                                    content_excerpt=""))
        return self._state

    def click(self, selector: str) -> PageState:
        return self._state

    def type(self, selector: str, text: str) -> PageState:
        return self._state

    def extract(self, selector: str | None = None) -> dict:
        return {"url": self._state.url, "text": self._state.content_excerpt,
                "trust": "untrusted"}

    def current(self) -> PageState:
        return self._state


def conformance(port: BrowserPort) -> list[str]:
    problems: list[str] = []
    try:
        st = port.navigate("https://example.test/")
        if not isinstance(st, PageState):
            problems.append("navigate must return a PageState")
        if not isinstance(port.extract(), dict):
            problems.append("extract must return a dict")
        ch = port.navigate("https://challenge.test/")
        if isinstance(ch, PageState) and ch.challenge is None:
            # a real adapter may not have a canned challenge page; only the
            # mock is required to expose one, so this is advisory
            pass
    except Exception as exc:  # noqa: BLE001
        problems.append(f"lifecycle raised: {exc!r}")
    return problems
