"""Decision Supervisor.

A dedicated security component that issues a verdict on every
significant decision at every level - not only external actions.
Every verdict is an auditable event; the human can override any
verdict from the GUI in both directions, and overrides feed the
supervisor's own audit (spec: Decision Supervisor).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum

from ..config import Config
from ..events import Actor, Ev, Event
from .budgets import BudgetProjection
from .guardrails import Flexibility, GuardrailStore
from .taint import TaintTracker


class RiskClass(str, Enum):
    READ_ONLY = "READ_ONLY"
    LOW_IMPACT_WRITE = "LOW_IMPACT_WRITE"
    EXTERNAL_COMMUNICATION = "EXTERNAL_COMMUNICATION"
    FINANCIAL = "FINANCIAL"
    IDENTITY = "IDENTITY"
    IRREVERSIBLE = "IRREVERSIBLE"


RISK_ORDER = {r.value: i for i, r in enumerate(RiskClass)}


class DecisionKind(str, Enum):
    GOAL_MODIFICATION = "GOAL_MODIFICATION"
    STRATEGY_SELECTION = "STRATEGY_SELECTION"
    RESOURCE_ALLOCATION = "RESOURCE_ALLOCATION"
    TOOL_INVOCATION = "TOOL_INVOCATION"
    EXTERNAL_COMMUNICATION = "EXTERNAL_COMMUNICATION"


class VerdictStatus(str, Enum):
    GRANTED = "GRANTED"
    DENIED = "DENIED"
    HUMAN_REQUIRED = "HUMAN_REQUIRED"


@dataclass
class ProposedDecision:
    kind: str
    action_name: str
    params: dict
    cost: float = 0.0
    risk_class: str = RiskClass.READ_ONLY.value
    goal_refs: list = field(default_factory=list)
    derived_from: list = field(default_factory=list)  # content ids the proposal drew on
    tainted: bool = False
    expected: dict = field(default_factory=dict)
    success_prob: float = 0.8
    rationale: str = ""
    id: str = field(default_factory=lambda: f"dec_{uuid.uuid4().hex[:10]}")

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def _matches(matcher: dict, decision: ProposedDecision) -> bool:
    for k, v in matcher.items():
        if k == "risk_class_at_least":
            if RISK_ORDER[decision.risk_class] < RISK_ORDER[v]:
                return False
        elif k == "kind" and decision.kind != v:
            return False
        elif k == "action_name" and decision.action_name != v:
            return False
        elif k == "goal_level_in":
            if decision.params.get("kind") not in v:
                return False
    return True


def _rule_triggered(rule: dict, decision: ProposedDecision,
                    budgets: BudgetProjection,
                    grounding=None) -> tuple[bool, str]:
    kind = rule.get("kind")
    if kind == "ground_check":
        from .grounding import ground_check
        return ground_check(rule, decision, grounding)
    if kind == "single_action_cost_limit":
        if decision.cost > float(rule["max"]):
            return True, f"action cost {decision.cost} exceeds limit {rule['max']}"
    elif kind == "budget_cap":
        rem = budgets.remaining(rule["resource"])
        if decision.cost > rem:
            return True, (f"cost {decision.cost} exceeds remaining "
                          f"{rule['resource']} budget {rem}")
    elif kind == "goal_ratification":
        if (decision.kind == DecisionKind.GOAL_MODIFICATION.value
                and decision.params.get("kind") in rule.get("levels", [])):
            return True, "meta/persistent goals require explicit human ratification"
    elif kind == "tainted_high_impact":
        min_class = rule.get("risk_class_at_least", RiskClass.FINANCIAL.value)
        if decision.tainted and RISK_ORDER[decision.risk_class] >= RISK_ORDER[min_class]:
            return True, ("high-impact action within the taint window of "
                          "recently ingested external content")
    elif kind == "behavior_block":
        if decision.action_name in rule.get("blocked", []):
            return True, f"behavior '{decision.action_name}' is on the blocked list"
    elif kind == "apprentice_domain":
        if (decision.params.get("domain") == rule.get("domain")
                and RISK_ORDER[decision.risk_class]
                >= RISK_ORDER[rule.get("risk_class_at_least", RiskClass.FINANCIAL.value)]):
            return True, (f"apprentice mode: calibration in domain "
                          f"'{rule.get('domain')}' is poor; human review required")
    return False, ""


class Supervisor:
    def __init__(self, runtime, guardrails: GuardrailStore,
                 budgets: BudgetProjection, taint: TaintTracker,
                 config: Config | None = None, grounding=None):
        self.runtime = runtime
        self.guardrails = guardrails
        self.budgets = budgets
        self.taint = taint
        self.config = config or Config()
        self.grounding = grounding

    def evaluate(self, decision: ProposedDecision, cycle: int | None,
                 advisories: list[str] | None = None,
                 escalate: list[str] | None = None) -> dict:
        # taint stamping happens here so no upstream component can forget it
        if not decision.tainted:
            decision.tainted = bool(decision.derived_from) or self.taint.tainted(cycle)

        status = VerdictStatus.GRANTED.value
        reasons: list[str] = [f"[advisory] {a}" for a in (advisories or [])]
        reasons += [f"[review] {e}" for e in (escalate or [])]
        triggered: list[str] = []
        for g in self.guardrails.active():
            if not _matches(g.get("conditions", {}), decision):
                continue
            if any(_matches(x, decision) for x in g.get("exceptions", [])):
                continue
            if any(_matches(x, decision) for x in g.get("exclusions", [])):
                continue
            hit, why = _rule_triggered(g["rule"], decision, self.budgets,
                                       self.grounding)
            if not hit:
                continue
            triggered.append(g["id"])
            self.runtime.emit(Ev.GUARDRAIL_TRIGGERED,
                              {"guardrail_id": g["id"], "decision_id": decision.id,
                               "tier": g["tier"], "reason": why},
                              Actor.SUPERVISOR)
            if g["rule"].get("kind") == "tainted_high_impact":
                self.runtime.emit(Ev.INJECTION_SUSPECTED,
                                  {"decision_id": decision.id,
                                   "derived_from": decision.derived_from,
                                   "reason": why},
                                  Actor.SUPERVISOR)
            flex = g["flexibility"]
            reasons.append(f"[tier{g['tier']}/{flex}] {g['description']}: {why}")
            if flex == Flexibility.HARD_BLOCK.value:
                status = VerdictStatus.DENIED.value
            elif flex == Flexibility.SOFT_BLOCK.value and status != VerdictStatus.DENIED.value:
                status = VerdictStatus.HUMAN_REQUIRED.value
            # WARN / ADVISORY only annotate

        # cross-AI review disagreement in "human" mode: the final decision
        # is discussed with the human before being enacted (M29)
        if escalate and status == VerdictStatus.GRANTED.value:
            status = VerdictStatus.HUMAN_REQUIRED.value

        if (status == VerdictStatus.DENIED.value
                and any(self.guardrails.guardrails[t]["rule"].get("kind") == "budget_cap"
                        for t in triggered)):
            self.runtime.emit(Ev.BUDGET_EXHAUSTED,
                              {"decision_id": decision.id, "cost": decision.cost},
                              Actor.SUPERVISOR)

        verdict = {"id": self.runtime.next_id("ver"), "decision_id": decision.id,
                   "status": status, "reasons": reasons, "triggered": triggered}
        self.runtime.emit(Ev.SUPERVISOR_VERDICT,
                          {"verdict": verdict, "decision": decision.to_dict()},
                          Actor.SUPERVISOR)
        return verdict

    def override(self, verdict_id: str, actor: Actor, approve: bool, note: str = "") -> str:
        """Human override, in both directions; itself an auditable event."""
        if actor != Actor.HUMAN:
            raise PermissionError("only the human identity may override a verdict")
        effective = VerdictStatus.GRANTED.value if approve else VerdictStatus.DENIED.value
        self.runtime.emit(Ev.SUPERVISOR_OVERRIDE,
                          {"verdict_id": verdict_id, "effective": effective, "note": note},
                          actor)
        return effective


class InboxProjection:
    """Pending human decisions + recent verdicts, for the GUI decision inbox."""

    def __init__(self, keep_recent: int = 50):
        self.pending: dict[str, dict] = {}   # verdict_id -> {"verdict", "decision"}
        self.recent: list[dict] = []
        self.overrides: list[dict] = []
        self._keep = keep_recent

    def apply(self, ev: Event) -> None:
        if ev.type == Ev.SUPERVISOR_VERDICT.value:
            v = ev.payload["verdict"]
            entry = {"verdict": v, "decision": ev.payload["decision"], "ts": ev.ts}
            self.recent.append(entry)
            self.recent = self.recent[-self._keep:]
            if v["status"] == VerdictStatus.HUMAN_REQUIRED.value:
                self.pending[v["id"]] = entry
        elif ev.type == Ev.SUPERVISOR_OVERRIDE.value:
            self.overrides.append(dict(ev.payload, ts=ev.ts))
            self.pending.pop(ev.payload["verdict_id"], None)
