"""Strategy branching (spec: Hypothesis Engine / Strategy Branching).

Strategies are multi-step branches with a lifecycle:

    PROPOSED -> ACTIVE -> DEFERRED / FAILED / SUCCESSFUL   (+ PRUNED)

The LLM proposes competing branches (gateway role "strategies"); the
engine scores them deterministically against the graph (front-loaded
value via a per-step discount, minus known cost), selects one, prunes
dominated ones. The active branch guides arbitration through a small
adherence bonus - deliberately small, so genuine re-arbitration (a
better opportunity) still wins and produces an honest
STRATEGY_CHANGED + replan instead of tunnel vision. Steps already
satisfied, or whose factor left the active context, are skipped.
"""
from __future__ import annotations

from .arbitration import _goal_contribution
from .config import Config
from .events import Actor, Ev, Event


class StrategyProjection:
    def __init__(self):
        self.branches: dict[str, dict] = {}

    def apply(self, ev: Event) -> None:
        t, p = ev.type, ev.payload
        if t == Ev.STRATEGY_PROPOSED.value:
            b = p["branch"]
            self.branches[b["id"]] = b
        elif t == Ev.STRATEGY_SELECTED.value:
            b = self.branches.get(p["branch_id"])
            if b is not None:
                b["status"] = "ACTIVE"
        elif t == Ev.STRATEGY_UPDATED.value:
            b = self.branches.get(p["branch_id"])
            if b is not None:
                b.update(p.get("changes", {}))
        elif t == Ev.STRATEGY_CHANGED.value:
            b = self.branches.get(p["branch_id"])
            if b is not None:
                b["status"] = "DEFERRED"
        elif t == Ev.STRATEGY_COMPLETED.value:
            b = self.branches.get(p["branch_id"])
            if b is not None:
                b["status"] = "SUCCESSFUL"

    def active(self) -> dict | None:
        actives = sorted((b for b in self.branches.values()
                          if b["status"] == "ACTIVE"), key=lambda b: b["id"])
        return actives[0] if actives else None

    def snapshot(self) -> list[dict]:
        return sorted(self.branches.values(), key=lambda b: b["id"])


class StrategyEngine:
    def __init__(self, runtime, projection: StrategyProjection, gateway,
                 graph, budgets, config: Config | None = None):
        self.runtime = runtime
        self.projection = projection
        self.gateway = gateway
        self.graph = graph
        self.budgets = budgets
        self.config = config or Config()

    # ------------------------------------------------------------ planning
    def ensure(self, context: dict) -> None:
        """Plan when no branch is active. Planning context is graph-derived
        only - external content never steers strategy formation."""
        if self.projection.active() is not None or not context.get("factors"):
            return
        resp = self.gateway.ask("strategies",
                                {"goals": context["goals"],
                                 "factors": context["factors"],
                                 "budget": context["budget"]})
        branches = []
        for h in resp.hypotheses:
            if h.action_name != "strategy":
                continue
            steps = [s for s in h.params.get("steps", [])
                     if isinstance(s, dict) and s.get("action_name")]
            if not steps:
                continue
            b = {"id": self.runtime.next_id("str"),
                 "label": str(h.params.get("label", "strategy")),
                 "steps": steps, "status": "PROPOSED", "step_index": 0,
                 "failures": 0, "score": round(self._score(steps), 4)}
            branches.append(b)
            self.runtime.emit(Ev.STRATEGY_PROPOSED, {"branch": b}, Actor.SYSTEM)
        if not branches:
            return
        best = max(branches, key=lambda b: (b["score"], b["id"]))
        self.runtime.emit(Ev.STRATEGY_SELECTED,
                          {"branch_id": best["id"], "score": best["score"]},
                          Actor.SYSTEM)
        for b in branches:
            if (b is not best
                    and b["score"] < best["score"] * self.config.strategy_prune_ratio):
                self.runtime.emit(Ev.STRATEGY_UPDATED,
                                  {"branch_id": b["id"],
                                   "changes": {"status": "PRUNED"}},
                                  Actor.SYSTEM)

    def _score(self, steps: list[dict]) -> float:
        limit = max(self.budgets.limit("money"), 1.0)
        seen: list[str] = []
        for s in steps:
            fid = s.get("factor_id")
            if fid and fid not in seen:
                seen.append(fid)
        score, cost_sum = 0.0, 0.0
        for i, fid in enumerate(seen):
            gross, _, _ = _goal_contribution(self.graph, fid, 0.9)
            score += gross * (self.config.strategy_step_discount ** i)
            f = self.graph.node(fid)
            if f is not None:
                p = f["props"]
                if p.get("unit_cost") is not None:
                    need = max(p.get("quantity_needed", 1)
                               - p.get("acquired_qty", 0), 0)
                    cost_sum += float(p["unit_cost"]) * need
        return score - (cost_sum / limit) * 0.2

    # ---------------------------------------------------------- execution
    def current_step_ref(self, allowed_factors: set[str]) -> tuple[str, dict] | None:
        """The active branch's next actionable step. Satisfied steps and
        steps whose factor left the active context are skipped; an
        exhausted branch completes."""
        b = self.projection.active()
        if b is None:
            return None
        i = b["step_index"]
        steps = b["steps"]
        while i < len(steps):
            s = steps[i]
            fid = s.get("factor_id")
            f = self.graph.node(fid) if fid else None
            if f is None or f["status"] != "ACTIVE" or fid not in allowed_factors:
                i += 1
                continue
            p = f["props"]
            if (s["action_name"] == "research_price"
                    and p.get("cost_confidence", 0.3) >= 0.6):
                i += 1
                continue
            if (s["action_name"] == "purchase"
                    and p.get("acquired_qty", 0) >= p.get("quantity_needed", 1)):
                i += 1
                continue
            break
        if i != b["step_index"]:
            self.runtime.emit(Ev.STRATEGY_UPDATED,
                              {"branch_id": b["id"],
                               "changes": {"step_index": i}}, Actor.SYSTEM)
        if i >= len(steps):
            self.runtime.emit(Ev.STRATEGY_COMPLETED, {"branch_id": b["id"]},
                              Actor.SYSTEM)
            return None
        return b["id"], steps[i]

    def note_execution(self, step_ref: tuple[str, dict] | None,
                       decision, success: bool) -> None:
        """Bookkeeping after an executed action: adherence advances the
        branch, failure counts toward FAILED, a deviation defers the
        branch (honest replan next cycle)."""
        if step_ref is None:
            return
        branch_id, step = step_ref
        b = self.projection.branches.get(branch_id)
        if b is None or b["status"] != "ACTIVE":
            return
        matched = (decision.action_name == step.get("action_name")
                   and decision.params.get("factor_id") == step.get("factor_id"))
        if matched:
            if success:
                self.runtime.emit(Ev.STRATEGY_UPDATED,
                                  {"branch_id": branch_id,
                                   "changes": {"step_index": b["step_index"] + 1,
                                               "failures": 0}},
                                  Actor.SYSTEM)
                if b["step_index"] >= len(b["steps"]):
                    self.runtime.emit(Ev.STRATEGY_COMPLETED,
                                      {"branch_id": branch_id}, Actor.SYSTEM)
            else:
                failures = b.get("failures", 0) + 1
                changes = {"failures": failures}
                if failures >= self.config.strategy_max_step_failures:
                    changes["status"] = "FAILED"
                self.runtime.emit(Ev.STRATEGY_UPDATED,
                                  {"branch_id": branch_id, "changes": changes},
                                  Actor.SYSTEM)
        else:
            self.runtime.emit(Ev.STRATEGY_CHANGED,
                              {"branch_id": branch_id,
                               "expected_step": step,
                               "executed": {"action_name": decision.action_name,
                                            "factor_id":
                                            decision.params.get("factor_id")},
                               "reason": "arbitration preferred a different "
                                         "action; branch deferred for replan"},
                              Actor.SYSTEM)
