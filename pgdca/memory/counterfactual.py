"""Counterfactual analysis (spec: Counterfactual Analysis).

For each executed decision: what was the best alternative at decision
time, and how much regret did the actual outcome leave? Counterfactual
values are labeled estimates - they come from ex-ante utilities, never
from pretending to know the untaken path's outcome. The distinction
feeds auditing: a good decision that failed by bad luck shows regret
without a decision-quality penalty.
"""
from __future__ import annotations

from ..events import Actor, Ev


class CounterfactualEngine:
    def __init__(self, runtime):
        self.runtime = runtime

    def analyze(self, record: dict) -> dict | None:
        decision = record["decision"]
        alternatives = record.get("alternatives", [])
        if len(alternatives) < 2:
            return None
        selected = next((a for a in alternatives
                         if a["action_name"] == decision["action_name"]
                         and a["params"].get("factor_id")
                         == decision["params"].get("factor_id")), None)
        others = [a for a in alternatives if a is not selected]
        if selected is None or not others:
            return None
        best_alt = max(others, key=lambda a: a["utility"])
        success = bool((record.get("outcome") or {}).get("success"))
        # realized value: the ex-ante utility if the action worked, a loss of
        # the sunk normalized cost if it did not (estimate, not ground truth)
        cost_norm = float(selected["parts"].get("cost_norm", 0.0))
        realized = selected["utility"] if success else -cost_norm
        regret = round(max(0.0, best_alt["utility"] - realized), 4)
        payload = {
            "decision_id": decision["id"],
            "estimate": True,
            "selected": {"action_name": selected["action_name"],
                         "factor_id": selected["params"].get("factor_id"),
                         "ex_ante_utility": selected["utility"]},
            "realized_value": round(realized, 4),
            "best_alternative": {"action_name": best_alt["action_name"],
                                 "factor_id": best_alt["params"].get("factor_id"),
                                 "ex_ante_utility": best_alt["utility"]},
            "regret": regret,
            # avoidable = the action failed AND a better-scored alternative
            # existed at decision time (else it was bad luck, not bad judgment)
            "avoidable": (not success
                          and best_alt["utility"] > selected["utility"]),
        }
        self.runtime.emit(Ev.COUNTERFACTUAL_ANALYZED, payload, Actor.SYSTEM)
        return payload
