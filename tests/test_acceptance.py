"""Phase 0 acceptance scenario + deterministic replay.

The executable acceptance test of the Minimum Viable Loop: persistent
goals with a budget, cross-goal antagonism, a human-approval flow, a
scripted environment failure, substitution of an unaffordable factor,
an adversarial injection caught by taint + supervisor, learned policy,
and byte-level deterministic replay from the event log.
"""
from __future__ import annotations

import json

from pgdca.cognition.gateway import ReplayLlmAdapter
from pgdca.controller import SysState
from pgdca.events import Ev
from pgdca.scenario.toy import create
from tests.conftest import drive, events_of


def test_full_scenario_with_injection(ctrl_env):
    ctrl, env = ctrl_env
    last = drive(ctrl, inject_after_first_approval=True)

    # 1. the loop closes: all targets satisfied, system idle
    assert last.status == "idle" and ctrl.state == SysState.IDLE
    for tid in ("t_boots", "t_helmet", "t_snacks"):
        assert ctrl.graph.node(tid)["status"] == "COMPLETED"

    # 2. hard budget respected to the cent
    b = ctrl.budgets.snapshot()["money"]
    assert b["spent"] <= b["limit"] == 500.0

    # 3. rational ordering: the critical non-substitutable enabler first
    bought = [p["factor_id"] for p in env.purchases]
    assert bought.index("boots") < bought.index("fruit")
    assert "bars" not in bought                       # substituted, not bought
    assert ctrl.graph.node("bars")["status"] == "SUPERSEDED"

    # 4. cross-goal antagonism was detected and recorded
    conflicts = events_of(ctrl, Ev.CONFLICT_DETECTED.value)
    assert any(c.payload.get("factor") == "bars" for c in conflicts)

    # 5. the injected offer was caught: taint -> human -> denied
    assert events_of(ctrl, Ev.INJECTION_SUSPECTED.value)
    injected = [r for r in ctrl.journal.records.values()
                if r["decision"].get("derived_from")]
    assert injected, "the naive LLM proposal from the advert must exist"
    for r in injected:
        assert r["verdict"]["status"] == "HUMAN_REQUIRED"
        assert r["override"] and r["override"]["effective"] == "DENIED"
        assert not r.get("execution")
    assert all(p["total_cost"] != 5.0 for p in env.purchases)  # no fake-price buy
    # the substitute was eventually bought at its real market price
    fruit = [p for p in env.purchases if p["factor_id"] == "fruit"]
    assert fruit and fruit[0]["total_cost"] == 20.0

    # 6. deterministic authority: nothing executed without a verdict
    for r in ctrl.journal.records.values():
        if r.get("execution"):
            granted = (r["verdict"] and r["verdict"]["status"] == "GRANTED") or \
                      (r["override"] and r["override"]["effective"] == "GRANTED")
            assert granted, f"decision {r['decision_id']} executed without authority"

    # 7. the big purchase went through the human (soft-block at 300)
    boots = [r for r in ctrl.journal.records.values()
             if r["decision"]["params"].get("factor_id") == "boots"
             and r["decision"]["action_name"] == "purchase"]
    assert boots and boots[0]["verdict"]["status"] == "HUMAN_REQUIRED"
    assert boots[0]["override"]["effective"] == "GRANTED"

    # 8. experience became policy; journal supports deliberation
    assert any(p["provenance"] == "learned" for p in ctrl.policies.snapshot())
    rat = ctrl.journal.rationale(boots[0]["decision_id"])
    assert rat["alternatives_considered"] and rat["what_happened"]["outcome"]


def test_deterministic_replay_reproduces_decisions():
    ctrl1, _ = create()
    drive(ctrl1)  # no injection: a fully scripted deterministic run
    events1 = ctrl1.runtime.events()

    ctrl2, _ = create(adapter=ReplayLlmAdapter(events1, strict=True))
    drive(ctrl2)
    events2 = ctrl2.runtime.events()

    keep = {Ev.DECISION_MADE.value, Ev.SUPERVISOR_VERDICT.value,
            Ev.ACTION_EXECUTED.value, Ev.ACTION_FAILED.value,
            Ev.RESOURCE_SPENT.value, Ev.TARGET_COMPLETED.value,
            Ev.AUDIT_COMPLETED.value}

    def trace(evs):
        return [(e.type, e.cycle, json.dumps(e.payload, sort_keys=True))
                for e in evs if e.type in keep]

    t1, t2 = trace(events1), trace(events2)
    assert t1 == t2 and len(t1) > 10
    # timestamps too: the deterministic clock makes replay byte-identical
    assert [e.ts for e in events1] == [e.ts for e in events2]
