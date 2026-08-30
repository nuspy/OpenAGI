"""Self-model: what the system knows about its own reliability.

Tracks per-(domain, action) attempts and outcomes, escalations, and
behavioral-recurrence statistics per context signature. Its central
duty is **calibrated priors**: the LLM may propose success
probabilities, but structured validators and historical data calibrate
them (spec: Importance/Utility/Cost/Probability) - claimed values
shrink toward the observed rate as evidence accumulates.
"""
from __future__ import annotations

from ..config import Config
from ..events import Ev, Event
from .policies import PolicyProjection


class SelfModelProjection:
    def __init__(self, config: Config | None = None):
        self.config = config or Config()
        self._pending: dict[str, tuple[str, str]] = {}   # decision_id -> (domain, action)
        self.actions: dict[str, dict] = {}               # "domain/action" -> stats
        self.signature_outcomes: dict[str, dict] = {}    # signature -> {"success","failure"}
        self.escalations: int = 0

    def apply(self, ev: Event) -> None:
        t, p = ev.type, ev.payload
        if t == Ev.DECISION_MADE.value:
            d = p["decision"]
            domain = d.get("params", {}).get("domain", "general")
            self._pending[d["id"]] = (domain, d["action_name"])
        elif t == Ev.OUTCOME_RECORDED.value:
            key = self._pending.pop(p.get("decision_id", ""), None)
            if key is not None:
                s = self.actions.setdefault("/".join(key),
                                            {"attempts": 0, "successes": 0})
                s["attempts"] += 1
                if p.get("success"):
                    s["successes"] += 1
        elif t == Ev.AUDIT_COMPLETED.value:
            sig = PolicyProjection.signature(p.get("features", {}))
            s = self.signature_outcomes.setdefault(sig, {"success": 0, "failure": 0})
            if p.get("outcome_quality", 1.0) < 0.5:
                s["failure"] += 1
            else:
                s["success"] += 1
        elif t == Ev.DELIBERATION_RESOLVED.value:
            # contested decision classes are remembered: a human who
            # cancelled or modified a decision in deliberation leaves a
            # dissent mark on its context signature
            res = p.get("resolution") or {}
            sig = res.get("signature")
            if sig and res.get("outcome") in ("cancelled", "modified"):
                s = self.signature_outcomes.setdefault(
                    sig, {"success": 0, "failure": 0})
                s["dissent"] = s.get("dissent", 0) + 1
        elif t == Ev.HUMAN_ESCALATION.value:
            self.escalations += 1

    # ----------------------------------------------------------- queries
    def stats(self, domain: str, action: str) -> dict:
        return self.actions.get(f"{domain}/{action}", {"attempts": 0, "successes": 0})

    def calibrated_success(self, domain: str, action: str, claimed: float) -> float:
        """Shrink the claimed probability toward the observed rate:
        (claimed*k + successes) / (k + attempts). No history -> claimed."""
        s = self.stats(domain, action)
        if s["attempts"] == 0:
            return claimed
        k = self.config.calibration_pseudo_count
        return round((claimed * k + s["successes"]) / (k + s["attempts"]), 4)

    def recurrence(self, signature: str) -> dict:
        return self.signature_outcomes.get(signature, {"success": 0, "failure": 0})

    def recurrence_advisory(self, signature: str) -> str | None:
        r = self.recurrence(signature)
        if (r["failure"] >= self.config.recurrence_failure_threshold
                and r["failure"] > r["success"]):
            return (f"this decision resembles {r['failure']} previously failed "
                    f"episodes (vs {r['success']} successes) with the same "
                    f"context signature")
        return None

    def dissent_advisory(self, signature: str) -> str | None:
        d = self.recurrence(signature).get("dissent", 0)
        if d >= self.config.dissent_advisory_threshold:
            return (f"the human contested {d} similar decision(s) in "
                    f"deliberation (revoked or modified after discussion)")
        return None

    def snapshot(self) -> dict:
        return {
            "actions": {k: dict(v, observed_rate=round(
                v["successes"] / v["attempts"], 3) if v["attempts"] else None)
                for k, v in sorted(self.actions.items())},
            "recurrence": dict(sorted(self.signature_outcomes.items())),
            "escalations": self.escalations,
        }
