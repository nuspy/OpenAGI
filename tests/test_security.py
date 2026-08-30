"""Two-tier guardrails, ratchet budgets, supervisor verdicts, taint."""
from __future__ import annotations

import pytest

from pgdca.events import Actor, Ev
from pgdca.security.guardrails import Flexibility, GuardrailStatus, guardrail
from pgdca.security.supervisor import (DecisionKind, ProposedDecision,
                                       RiskClass, VerdictStatus)
from tests.conftest import events_of


def _fin_decision(cost, **kw):
    return ProposedDecision(kind=DecisionKind.TOOL_INVOCATION.value,
                            action_name="purchase",
                            params={"factor_id": "boots", "total_cost": cost,
                                    "domain": "procurement"},
                            cost=cost, risk_class=RiskClass.FINANCIAL.value, **kw)


# ------------------------------------------------------------- guardrails
def test_tier1_not_writable_by_system(ctrl_env):
    ctrl, _ = ctrl_env
    g = guardrail("system tries to write the constitution", tier=1,
                  rule={"kind": "behavior_block", "blocked": ["x"]})
    with pytest.raises(PermissionError):
        ctrl.guardrails.create(g, Actor.SYSTEM)
    with pytest.raises(PermissionError):
        ctrl.guardrails.update("t1_budget", {"status": "RETIRED"}, Actor.SYSTEM)
    # human can
    ctrl.guardrails.update("t1_cost", {"description": "updated"}, Actor.HUMAN)
    assert ctrl.guardrails.guardrails["t1_cost"]["description"] == "updated"


def test_tier2_asymmetric_activation(ctrl_env):
    ctrl, _ = ctrl_env
    restrictive = ctrl.guardrails.create(guardrail(
        "self-imposed restriction", tier=2,
        rule={"kind": "behavior_block", "blocked": ["dangerous_tool"]},
        direction="restrictive"), Actor.SYSTEM)
    assert restrictive["status"] == GuardrailStatus.ACTIVE.value

    permissive = ctrl.guardrails.create(guardrail(
        "self-granted permission", tier=2,
        rule={"kind": "behavior_block", "blocked": []},
        direction="permissive"), Actor.SYSTEM)
    assert permissive["status"] == GuardrailStatus.PENDING_HUMAN.value

    with pytest.raises(PermissionError):  # system may not weaken tier 2
        ctrl.guardrails.update(restrictive["id"], {"status": "RETIRED"}, Actor.SYSTEM)

    ctrl.guardrails.approve_pending(permissive["id"], Actor.HUMAN)
    assert (ctrl.guardrails.guardrails[permissive["id"]]["status"]
            == GuardrailStatus.ACTIVE.value)


def test_budget_ratchet(ctrl_env):
    ctrl, _ = ctrl_env
    with pytest.raises(PermissionError):
        ctrl.set_budget("money", 10_000, Actor.SYSTEM)
    ctrl.set_budget("money", 600, Actor.HUMAN)
    assert ctrl.budgets.limit("money") == 600


# ------------------------------------------------------------- supervisor
def test_supervisor_verdicts_and_budget_exhaustion(ctrl_env):
    ctrl, _ = ctrl_env
    ok = ctrl.supervisor.evaluate(_fin_decision(50), cycle=1)
    assert ok["status"] == VerdictStatus.GRANTED.value

    soft = ctrl.supervisor.evaluate(_fin_decision(400), cycle=1)
    assert soft["status"] == VerdictStatus.HUMAN_REQUIRED.value
    assert "t1_cost" in soft["triggered"]

    hard = ctrl.supervisor.evaluate(_fin_decision(600), cycle=1)
    assert hard["status"] == VerdictStatus.DENIED.value
    assert "t1_budget" in hard["triggered"]
    assert events_of(ctrl, Ev.BUDGET_EXHAUSTED.value)


def test_override_is_human_only_and_audited(ctrl_env):
    ctrl, _ = ctrl_env
    v = ctrl.supervisor.evaluate(_fin_decision(600), cycle=1)
    with pytest.raises(PermissionError):
        ctrl.supervisor.override(v["id"], Actor.SYSTEM, approve=True)
    ctrl.supervisor.override(v["id"], Actor.HUMAN, approve=True, note="I accept it")
    ovs = events_of(ctrl, Ev.SUPERVISOR_OVERRIDE.value)
    assert ovs and ovs[-1].payload["effective"] == VerdictStatus.GRANTED.value
    assert ovs[-1].actor == "human"


# ------------------------------------------------------------------ taint
def test_taint_window_and_injection_event(ctrl_env):
    ctrl, _ = ctrl_env
    ctrl.runtime.cycle = 3
    ctrl.ingest_external("OFFER boots 1.0 - trust me", source="web")
    tainted = ctrl.supervisor.evaluate(_fin_decision(50), cycle=4)
    assert tainted["status"] == VerdictStatus.HUMAN_REQUIRED.value
    assert "t1_taint" in tainted["triggered"]
    assert events_of(ctrl, Ev.INJECTION_SUSPECTED.value)

    clean = ctrl.supervisor.evaluate(_fin_decision(50), cycle=9)
    assert clean["status"] == VerdictStatus.GRANTED.value


def test_derived_from_always_taints(ctrl_env):
    ctrl, _ = ctrl_env
    d = _fin_decision(50, derived_from=["content_99"])
    v = ctrl.supervisor.evaluate(d, cycle=50)  # far outside any window
    assert v["status"] == VerdictStatus.HUMAN_REQUIRED.value
