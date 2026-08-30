"""Taint tracking: external content is data, never instructions.

Every ingested item carries provenance; recently ingested external
content taints subsequent high-impact decisions, which then require
elevated authorization (spec: Prompt Injection Defense).
"""
from __future__ import annotations

from ..config import Config
from ..events import Ev, Event


class TaintTracker:
    def __init__(self, config: Config | None = None):
        self.config = config or Config()
        self.contents: list[dict] = []          # {"id", "cycle", "trust", "source"}
        self._last_external_cycle: int | None = None

    def apply(self, ev: Event) -> None:
        if ev.type == Ev.CONTENT_INGESTED.value:
            p = ev.payload
            self.contents.append({"id": p["content_id"], "cycle": ev.cycle,
                                  "trust": p.get("trust", "external"),
                                  "source": p.get("source", "unknown")})
            if p.get("trust", "external") == "external" and ev.cycle is not None:
                self._last_external_cycle = ev.cycle

    def tainted(self, cycle: int | None) -> bool:
        if cycle is None or self._last_external_cycle is None:
            return False
        return (cycle - self._last_external_cycle) <= self.config.taint_window_cycles

    def external_content_ids(self) -> set[str]:
        return {c["id"] for c in self.contents if c["trust"] == "external"}
