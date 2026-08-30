"""Dynamic reprioritization scenario: the "meetings vs mountain" example
from the PGDCA design documents.

A mountain trip is being prepared when a business opportunity appears
that contributes far more to a higher-priority persistent goal
(financial independence). The system does not "break its plan": it
re-evaluates it - the opportunity wins the budget, the starved trip
targets are DEFERRED (revisitable, not abandoned), and the affordable
part of the plan (snack substitution) still completes. The persistent
goals themselves never change without the human.
"""
from __future__ import annotations

from ..domain import NodeKind, RelType, ValidationStatus, edge, node
from ..events import Actor, Ev
from .toy import ToyEnvironment, build_world, create as toy_create


def create(db_path: str = ":memory:"):
    env = ToyEnvironment(prices={"boots": 400.0, "helmet": 80.0,
                                 "bars": 20.0, "fruit": 2.0,
                                 "meeting_ticket": 450.0},
                         fail_once=())
    ctrl, env = toy_create(db_path=db_path, env=env)
    # a higher-priority persistent goal, ratified by the human at build time
    ctrl.runtime.emit(Ev.NODE_ADDED, {"node": node(
        "fin_indep", NodeKind.PERSISTENT_GOAL, "Financial independence",
        priority=0.95)}, Actor.HUMAN)
    return ctrl, env


def inject_meeting_opportunity(ctrl) -> None:
    """The environment discovers the opportunity mid-run: an investor
    meeting whose ticket strongly supports financial independence."""
    E = Actor.ENVIRONMENT
    V = ValidationStatus.VALIDATED
    ctrl.runtime.emit(Ev.OPPORTUNITY_DETECTED, {
        "opportunity_id": "opp_meeting",
        "description": "investor meetings during the trip week",
        "affects_goal": "fin_indep", "expected_value": 0.9,
        "cost": 450.0}, E)
    ctrl.runtime.emit(Ev.NODE_ADDED, {"node": node(
        "meeting_ticket", NodeKind.FACTOR, "Investor meeting ticket",
        importance=0.95, substitutability=0.05, quantity_needed=1,
        acquired_qty=0, unit_cost=450.0, cost_confidence=0.95)}, E)
    ctrl.runtime.emit(Ev.NODE_ADDED, {"node": node(
        "t_meeting", NodeKind.TARGET, "Attend the investor meetings")}, E)
    ctrl.runtime.emit(Ev.EDGE_ADDED, {"edge": edge(
        "e_m_tm", "meeting_ticket", "t_meeting", RelType.REQUIRED, V,
        "environment", importance=0.95, confidence=0.95)}, E)
    ctrl.runtime.emit(Ev.EDGE_ADDED, {"edge": edge(
        "e_m_fin", "meeting_ticket", "fin_indep", RelType.SUPPORT, V,
        "environment", importance=0.95, confidence=0.95,
        substitutability=0.05)}, E)
    ctrl.runtime.emit(Ev.EDGE_ADDED, {"edge": edge(
        "e_tm_fin", "t_meeting", "fin_indep", RelType.SUPPORT, V,
        "environment", importance=0.9, confidence=0.95)}, E)
    # independence also serves the meta-goal: a second, distinct goal path
    ctrl.runtime.emit(Ev.EDGE_ADDED, {"edge": edge(
        "e_m_wb", "meeting_ticket", "wellbeing", RelType.SUPPORT, V,
        "environment", importance=0.8, confidence=0.9)}, E)


def main() -> None:  # pragma: no cover - manual demo runner
    ctrl, env = create()
    ctrl.step()                      # research the most important factor
    inject_meeting_opportunity(ctrl)
    for _ in range(30):
        results = ctrl.run(30)
        last = results[-1] if results else None
        if last is None or last.status in ("idle", "stopped", "escalated"):
            break
        if last.status == "waiting_human":
            d = ctrl.pending_decision()["decision"]
            print(f"[inbox] {d.action_name} {d.params} -> APPROVE")
            ctrl.resolve_pending(True, "demo approval")
    print("\n--- summary ---")
    print("purchases:", env.purchases)
    for tid in ("t_meeting", "t_boots", "t_helmet", "t_snacks"):
        print(f"  {tid}: {ctrl.graph.node(tid)['status']}")
    print("summit goal:", ctrl.graph.node("summit")["status"],
          "| fin_indep goal:", ctrl.graph.node("fin_indep")["status"])


if __name__ == "__main__":  # pragma: no cover
    main()
