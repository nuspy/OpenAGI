"""Decision journal: the auditable record of every decision.

A projection over decision-related events; also serves deliberation -
the human can open any decision and get the reconstructed rationale
(evidence, alternatives with scores, verdicts, outcomes, audits).
"""
from __future__ import annotations

from ..events import Ev, Event


class JournalProjection:
    def __init__(self):
        self.records: dict[str, dict] = {}
        self.order: list[str] = []
        self._verdict_to_decision: dict[str, str] = {}
        self.node_index: dict[str, list[str]] = {}  # node_id -> [decision_id]

    def apply(self, ev: Event) -> None:
        t, p = ev.type, ev.payload
        if t == Ev.DECISION_MADE.value:
            d = p["decision"]
            did = d["id"]
            self.records[did] = {
                "decision_id": did, "cycle": ev.cycle, "ts": ev.ts,
                "decision": d,
                "alternatives": p.get("alternatives", []),
                "context": p.get("context", {}),
                "conflicts": p.get("conflicts", []),
                "shadow_evaluations": [],
                "verdict": None, "override": None,
                "execution": None, "outcome": None,
                "verification": None, "audit": None,
            }
            self.order.append(did)
            refs = [d.get("params", {}).get("factor_id")] + list(d.get("goal_refs", []))
            for r in refs:
                if r:
                    self.node_index.setdefault(r, []).append(did)
        elif t == Ev.SUPERVISOR_VERDICT.value:
            v = p["verdict"]
            self._verdict_to_decision[v["id"]] = v["decision_id"]
            rec = self.records.get(v["decision_id"])
            if rec is not None:
                rec["verdict"] = v
        elif t == Ev.SUPERVISOR_OVERRIDE.value:
            did = self._verdict_to_decision.get(p["verdict_id"])
            rec = self.records.get(did) if did else None
            if rec is not None:
                rec["override"] = dict(p, ts=ev.ts)
        elif t in (Ev.ACTION_EXECUTED.value, Ev.ACTION_FAILED.value):
            rec = self.records.get(p.get("decision_id", ""))
            if rec is not None:
                rec["execution"] = {"status": "ok" if t == Ev.ACTION_EXECUTED.value else "failed",
                                    "result": p.get("result", {}), "error": p.get("error")}
        elif t == Ev.OUTCOME_RECORDED.value:
            rec = self.records.get(p.get("decision_id", ""))
            if rec is not None:
                rec["outcome"] = {k: v for k, v in p.items() if k != "decision_id"}
        elif t == Ev.VERIFICATION_COMPLETED.value:
            rec = self.records.get(p.get("decision_id", ""))
            if rec is not None:
                rec["verification"] = {k: v for k, v in p.items() if k != "decision_id"}
        elif t == Ev.AUDIT_COMPLETED.value:
            rec = self.records.get(p.get("decision_id", ""))
            if rec is not None:
                rec["audit"] = {k: v for k, v in p.items() if k != "decision_id"}
        elif t == Ev.COUNTERFACTUAL_ANALYZED.value:
            rec = self.records.get(p.get("decision_id", ""))
            if rec is not None:
                rec["counterfactual"] = {k: v for k, v in p.items()
                                         if k != "decision_id"}
        elif t == Ev.COMPENSATION_EXECUTED.value:
            rec = self.records.get(p.get("decision_id", ""))
            if rec is not None:
                rec["compensation"] = {k: v for k, v in p.items()
                                       if k != "decision_id"}
        elif t == Ev.REVIEW_COMPLETED.value:
            rec = self.records.get(p.get("decision_id", ""))
            if rec is not None:
                rec.setdefault("reviews", []).append(p["review"])
        elif t == Ev.POLICY_SHADOW_EVALUATED.value:
            rec = self.records.get(p.get("decision_id", ""))
            if rec is not None:
                rec["shadow_evaluations"].append(
                    {"policy_id": p["policy_id"], "agrees": p["agrees"]})

    def rationale(self, decision_id: str) -> dict | None:
        """Deliberation packet: why was this decision made?"""
        rec = self.records.get(decision_id)
        if rec is None:
            return None
        return {
            "decision_id": decision_id,
            "what": {"action": rec["decision"]["action_name"],
                     "params": rec["decision"]["params"]},
            "why": rec["decision"].get("rationale", ""),
            "evidence": rec["context"],
            "alternatives_considered": rec["alternatives"],
            "conflicts": rec["conflicts"],
            "expected": rec["decision"].get("expected", {}),
            "verdict": rec["verdict"],
            "override": rec["override"],
            "what_happened": {"execution": rec["execution"],
                              "outcome": rec["outcome"],
                              "verification": rec["verification"]},
            "audit": rec["audit"],
            "counterfactual": rec.get("counterfactual"),
            "compensation": rec.get("compensation"),
            "reviews": rec.get("reviews"),
        }

    def for_node(self, node_id: str) -> list[dict]:
        return [self.rationale(d) for d in self.node_index.get(node_id, [])]

    def tail(self, n: int = 20) -> list[dict]:
        return [self.records[d] for d in self.order[-n:]]
