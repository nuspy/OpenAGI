"""Strategy branching: proposal, selection, adherence, deviation, lifecycle."""
from __future__ import annotations

from pgdca.events import Ev
from pgdca.scenario.opportunity import (create as create_opportunity,
                                        inject_meeting_opportunity)
from tests.conftest import drive, events_of


def test_branches_proposed_selected_and_followed(ctrl_env):
    ctrl, _ = ctrl_env
    drive(ctrl)

    proposed = events_of(ctrl, Ev.STRATEGY_PROPOSED.value)
    assert len(proposed) >= 2, "competing branches must be proposed"
    selected = events_of(ctrl, Ev.STRATEGY_SELECTED.value)
    assert selected, "one branch must be selected"

    branches = {b["id"]: b for b in ctrl.strategies.snapshot()}
    first = branches[selected[0].payload["branch_id"]]
    assert first["label"] == "critical-enablers-first"  # scoring prefers it

    # adherence: decisions record their strategy step while on-plan
    on_plan = [r for r in ctrl.journal.records.values()
               if r["context"].get("strategy")]
    assert on_plan, "on-plan decisions must carry their branch/step"

    # lifecycle reached a terminal success somewhere
    statuses = {b["status"] for b in branches.values()}
    assert "SUCCESSFUL" in statuses
    # the support-first branch never wins selection
    assert all(b["status"] != "ACTIVE" or b["label"] != "support-items-first"
               for b in branches.values())


def test_deviation_defers_branch_and_replans(ctrl_env):
    ctrl, _ = ctrl_env
    drive(ctrl)
    changed = events_of(ctrl, Ev.STRATEGY_CHANGED.value)
    # the plan said "purchase bars"; arbitration preferred researching the
    # substitute - an honest deviation, then a replan that completes
    assert changed
    assert any(c.payload["expected_step"].get("factor_id") == "bars"
               for c in changed)
    assert {b["status"] for b in ctrl.strategies.snapshot()} & {"SUCCESSFUL"}
    assert events_of(ctrl, Ev.STRATEGY_COMPLETED.value)


def test_opportunity_causes_strategy_change():
    ctrl, env = create_opportunity()
    ctrl.step()
    inject_meeting_opportunity(ctrl)
    drive(ctrl)

    changed = events_of(ctrl, Ev.STRATEGY_CHANGED.value)
    assert changed, "the meeting must deflect the trip strategy"
    assert any(c.payload["executed"].get("factor_id") == "meeting_ticket"
               for c in changed)
    # the deflected branch is DEFERRED, a later branch completes
    statuses = [b["status"] for b in ctrl.strategies.snapshot()]
    assert "DEFERRED" in statuses and "SUCCESSFUL" in statuses
    bought = [p["factor_id"] for p in env.purchases]
    assert "meeting_ticket" in bought and "boots" not in bought


def test_adherence_bonus_is_visible_but_small(ctrl_env):
    ctrl, _ = ctrl_env
    drive(ctrl)
    bonused = []
    for r in ctrl.journal.records.values():
        for a in r["alternatives"]:
            if "strategy_bonus" in a.get("parts", {}):
                bonused.append(a)
    assert bonused, "the adherence bonus must be recorded in the journal"
    assert all(a["parts"]["strategy_bonus"] <= 0.05 for a in bonused)
