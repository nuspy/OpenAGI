"""Audit engine: decision quality is not outcome quality.

Decision quality is scored against the information available at
decision time (alternatives considered, cost confidence, warnings
heeded); outcome quality against what actually happened. A good
decision can fail by bad luck and a poor one can succeed by chance -
the two scores are stored separately (spec: Decision Quality vs
Outcome Quality).
"""
from __future__ import annotations

from ..config import Config
from ..events import Actor, Ev
from .calibration import CalibrationProjection


class AuditEngine:
    def __init__(self, runtime, calibration: CalibrationProjection,
                 config: Config | None = None):
        self.runtime = runtime
        self.calibration = calibration
        self.config = config or Config()

    def run(self, record: dict) -> dict:
        decision = record["decision"]
        ctx = record.get("context", {})

        # ---- decision quality: judged on information available at the time
        dq = 1.0
        deductions: list[str] = []
        if len(record.get("alternatives", [])) < 2:
            dq -= 0.2
            deductions.append("fewer than two alternatives considered")
        cost_conf = float(decision.get("params", {}).get("cost_confidence", 1.0))
        if decision["action_name"] == "purchase" and cost_conf < 0.6:
            dq -= 0.3
            deductions.append("acted on low-confidence cost without research")
        verdict = record.get("verdict") or {}
        warn_count = sum(1 for r in verdict.get("reasons", []) if "/WARN]" in r)
        dq -= 0.05 * warn_count
        if warn_count:
            deductions.append(f"{warn_count} guardrail warning(s) at decision time")
        dq = max(0.0, round(dq, 3))

        # ---- outcome quality: judged on what actually happened
        execution = record.get("execution") or {}
        verification = record.get("verification") or {}
        if execution.get("status") == "failed":
            oq = 0.1
        elif verification.get("matched") is True:
            oq = 1.0
        elif verification.get("matched") is False:
            oq = 0.4
        else:
            oq = 0.6

        # ---- error classification (different errors need different fixes)
        error_class = None
        if execution.get("status") == "failed":
            error_class = ("environmental_uncertainty"
                           if float(decision.get("success_prob", 0.8)) >= 0.7
                           else "risk_estimation_error")

        # ---- context features for behavioral-recurrence detection
        limit = float(ctx.get("budget_limit", 1.0)) or 1.0
        remaining = float(ctx.get("budget_remaining", limit))
        cost = float(decision.get("params", {}).get("total_cost", 0.0))
        fsnap = ctx.get("factor_snapshot", {})
        features = {
            "action": decision["action_name"],
            "domain": decision.get("params", {}).get("domain", "general"),
            "budget_constrained": (remaining - cost) < 0.5 * limit,
            "picked_high_importance_low_subst": (
                float(fsnap.get("importance", 0.0)) >= 0.7
                and float(fsnap.get("substitutability", 1.0)) <= 0.4),
        }

        payload = {"decision_id": decision["id"], "decision_quality": dq,
                   "outcome_quality": oq, "deductions": deductions,
                   "error_class": error_class, "features": features}
        self.runtime.emit(Ev.AUDIT_COMPLETED, payload, Actor.SYSTEM)
        if error_class:
            self.runtime.emit(Ev.ERROR_DETECTED,
                              {"decision_id": decision["id"], "class": error_class},
                              Actor.SYSTEM)
        domain = features["domain"]
        b = self.calibration.brier(domain)
        if b is not None:
            self.runtime.emit(Ev.CALIBRATION_UPDATED,
                              {"domain": domain, "brier": round(b, 4),
                               "samples": self.calibration.samples(domain)},
                              Actor.SYSTEM)
        return payload
