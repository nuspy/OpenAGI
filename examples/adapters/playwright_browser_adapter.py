"""Real agentic-browser adapter behind BrowserPort (Playwright/Chromium).

Setup (once, in the project venv):

    pip install playwright
    playwright install chromium

Configuration (env vars):

    PGDCA_BROWSER_HEADLESS   "0" shows the browser window (default headless)
    PGDCA_BROWSER_TIMEOUT_S  per-action timeout, default 30

Doctrine (enforced here and in the wrappers):
- page content returns as UNTRUSTED data (PageState.trust);
- challenge pages (CAPTCHA, Cloudflare, "verify you are human") are
  detected and surfaced as an explicit PageState.challenge - never
  bypassed: the controller escalates to the human (spec: CAPTCHA
  Handling).

The browser starts lazily at the first call and stays open; call
close() to release it.
"""
from __future__ import annotations

import os
import re

from pgdca.ports.browser import PageState

#: signals of a human-verification challenge in title/body (heuristic,
#: deliberately broad: a false positive costs one human look, a false
#: negative would mean silently acting behind a bot-wall)
_CHALLENGE_RE = re.compile(
    r"captcha|are you a robot|not a robot|verify you are human|"
    r"unusual traffic|cf-challenge|attention required|access denied|"
    r"just a moment|verifica di non essere un robot", re.I)


def detect_challenge(title: str, body_text: str) -> dict | None:
    sample = f"{title}\n{body_text[:4000]}"
    m = _CHALLENGE_RE.search(sample)
    if m:
        return {"provider": "generic", "type": "challenge",
                "matched": m.group(0).lower()}
    return None


class PlaywrightBrowserAdapter:
    def __init__(self, headless: bool | None = None,
                 timeout_s: float | None = None):
        self.headless = (os.environ.get("PGDCA_BROWSER_HEADLESS", "1") != "0"
                         if headless is None else headless)
        self.timeout_ms = 1000 * float(
            timeout_s or os.environ.get("PGDCA_BROWSER_TIMEOUT_S", 30))
        self._pw = None
        self._browser = None
        self._page = None

    def _ensure(self):
        if self._page is not None:
            return self._page
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise RuntimeError(
                "playwright non installato: pip install playwright && "
                "playwright install chromium")
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=self.headless)
        self._page = self._browser.new_page()
        self._page.set_default_timeout(self.timeout_ms)
        return self._page

    def _state(self) -> PageState:
        page = self._ensure()
        title, text = "", ""
        try:
            title = page.title()
            text = page.inner_text("body", timeout=5000)
        except Exception:  # noqa: BLE001 - blank/binary pages have no body
            pass
        return PageState(url=page.url, title=title,
                         content_excerpt=text[:4000],
                         challenge=detect_challenge(title, text),
                         trust="untrusted")

    # ---------------------------------------------------------- BrowserPort

    def navigate(self, url: str) -> PageState:
        page = self._ensure()
        try:
            page.goto(url, wait_until="domcontentloaded")
        except Exception as exc:  # noqa: BLE001 - unreachable host, TLS, ...
            return PageState(url=url, title="navigation failed",
                             content_excerpt=str(exc)[:500],
                             metadata={"error": str(exc)[:500]})
        return self._state()

    def click(self, selector: str) -> PageState:
        self._ensure().click(selector)
        return self._state()

    def type(self, selector: str, text: str) -> PageState:
        self._ensure().fill(selector, text)
        return self._state()

    def extract(self, selector: str | None = None) -> dict:
        page = self._ensure()
        if selector:
            texts = [el.inner_text() for el in page.query_selector_all(selector)]
            return {"url": page.url, "selector": selector,
                    "matches": texts[:50], "trust": "untrusted"}
        st = self._state()
        return {"url": st.url, "title": st.title,
                "text": st.content_excerpt, "trust": "untrusted"}

    def current(self) -> PageState:
        return self._state()

    def close(self) -> None:
        for closer in (lambda: self._browser.close(), lambda: self._pw.stop()):
            try:
                closer()
            except Exception:  # noqa: BLE001
                pass
        self._pw = self._browser = self._page = None
