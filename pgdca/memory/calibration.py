"""Calibration: Brier score per domain, from day one.

Predictions are captured at decision time, outcomes at observation
time; the mean Brier score per domain feeds apprentice mode (poorly
calibrated domains earn tighter supervision, not more autonomy).
"""
from __future__ import annotations

from ..config import Config
from ..events import Ev, Event


class CalibrationProjection:
    def __init__(self, config: Config | None = None):
        self.config = config or Config()
        self._pending: dict[str, tuple[str, float]] = {}  # decision_id -> (domain, p)
        self.domains: dict[str, dict] = {}                # domain -> {"sum_sq", "n"}

    def apply(self, ev: Event) -> None:
        if ev.type == Ev.DECISION_MADE.value:
            d = ev.payload["decision"]
            domain = d.get("params", {}).get("domain", "general")
            self._pending[d["id"]] = (domain, float(d.get("success_prob", 0.8)))
        elif ev.type == Ev.OUTCOME_RECORDED.value:
            did = ev.payload.get("decision_id")
            if did in self._pending:
                domain, p = self._pending.pop(did)
                s = self.domains.setdefault(domain, {"sum_sq": 0.0, "n": 0})
                outcome = 1.0 if ev.payload.get("success") else 0.0
                s["sum_sq"] += (p - outcome) ** 2
                s["n"] += 1

    def brier(self, domain: str) -> float | None:
        s = self.domains.get(domain)
        if not s or s["n"] == 0:
            return None
        return s["sum_sq"] / s["n"]

    def samples(self, domain: str) -> int:
        return self.domains.get(domain, {}).get("n", 0)

    def poorly_calibrated(self, domain: str) -> bool:
        b = self.brier(domain)
        return (b is not None
                and self.samples(domain) >= self.config.calibration_min_samples
                and b > self.config.calibration_poor_brier)

    def snapshot(self) -> dict:
        return {d: {"brier": round(s["sum_sq"] / s["n"], 4), "samples": s["n"]}
                for d, s in self.domains.items() if s["n"]}
