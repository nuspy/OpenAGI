"""Dynamic reprioritization: the meetings-vs-mountain example.

The system preserves its persistent goals while changing the route:
the higher-value opportunity wins the budget, starved targets are
DEFERRED (revisitable), the affordable remainder still completes.
"""
from __future__ import annotations

from pgdca.events import Ev
from pgdca.scenario.opportunity import create, inject_meeting_opportunity
from tests.conftest import drive, events_of


def test_opportunity_outcompetes_trip_and_defers_targets():
    ctrl, env = create()
    ctrl.step()                       # research the top factor first
    inject_meeting_opportunity(ctrl)
    last = drive(ctrl)
    assert last.status == "idle"

    bought = [p["factor_id"] for p in env.purchases]
    assert "meeting_ticket" in bought
    assert "boots" not in bought      # outcompeted, not bought

    assert ctrl.graph.node("t_meeting")["status"] == "COMPLETED"
    assert ctrl.graph.node("t_boots")["status"] == "DEFERRED"
    assert ctrl.graph.node("t_helmet")["status"] == "DEFERRED"
    assert ctrl.graph.node("t_snacks")["status"] == "COMPLETED"  # via substitute

    # persistent goals are never touched without the human
    assert ctrl.graph.node("summit")["status"] == "ACTIVE"
    assert ctrl.graph.node("fin_indep")["status"] == "ACTIVE"

    assert events_of(ctrl, Ev.OPPORTUNITY_DETECTED.value)
    deferred = events_of(ctrl, Ev.TARGET_DEFERRED.value)
    assert {e.payload["node_id"] for e in deferred} >= {"t_boots", "t_helmet"}
    assert events_of(ctrl, Ev.RESOURCE_REALLOCATED.value)

    # the big opportunity purchase still went through the human (>300)
    meeting = [r for r in ctrl.journal.records.values()
               if r["decision"]["params"].get("factor_id") == "meeting_ticket"]
    assert meeting and meeting[0]["verdict"]["status"] == "HUMAN_REQUIRED"
    assert meeting[0]["override"]["effective"] == "GRANTED"

    b = ctrl.budgets.snapshot()["money"]
    assert b["spent"] <= b["limit"] == 500.0


def test_no_spurious_deferrals_in_base_scenario(ctrl_env):
    ctrl, _ = ctrl_env
    drive(ctrl)
    assert not events_of(ctrl, Ev.TARGET_DEFERRED.value)
    for tid in ("t_boots", "t_helmet", "t_snacks"):
        assert ctrl.graph.node(tid)["status"] == "COMPLETED"
