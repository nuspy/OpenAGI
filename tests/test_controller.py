"""Corrigibility (STOP/PAUSE unconditional), goal ratification, human edits."""
from __future__ import annotations

import pytest

from pgdca.controller import SysState
from pgdca.domain import NodeKind
from pgdca.events import Actor, Ev
from tests.conftest import events_of


def test_stop_is_honored_before_any_execution(ctrl_env):
    ctrl, env = ctrl_env

    def stop_on_first_decision(ev):
        if ev.type == Ev.DECISION_MADE.value:
            ctrl.control("STOP", Actor.HUMAN)

    ctrl.runtime.subscribe(stop_on_first_decision)
    ctrl.run(10)
    assert ctrl.state == SysState.STOPPED
    assert events_of(ctrl, Ev.DECISION_MADE.value)          # a decision was made
    assert not events_of(ctrl, Ev.ACTION_EXECUTED.value)    # but nothing ran
    assert not env.purchases
    # and the system stays stopped
    r = ctrl.step()
    assert r.status == "stopped"
    assert not events_of(ctrl, Ev.ACTION_EXECUTED.value)


def test_pause_and_resume(ctrl_env):
    ctrl, _ = ctrl_env
    ctrl.control("PAUSE", Actor.HUMAN)
    r = ctrl.step()
    assert r.status == "paused" and ctrl.cycle == 0
    ctrl.control("RESUME", Actor.HUMAN)
    r2 = ctrl.step()
    assert r2.cycle == 1 and r2.status != "paused"


def test_control_commands_are_human_only(ctrl_env):
    ctrl, _ = ctrl_env
    with pytest.raises(PermissionError):
        ctrl.control("STOP", Actor.SYSTEM)


def test_goal_ratification_flow(ctrl_env):
    ctrl, _ = ctrl_env
    gid = ctrl.propose_goal(NodeKind.PERSISTENT_GOAL, "Learn the piano", 0.4,
                            actor=Actor.SYSTEM)
    assert ctrl.graph.node(gid)["status"] == "PROPOSED"
    with pytest.raises(PermissionError):
        ctrl.ratify_goal(gid, Actor.SYSTEM)
    ctrl.ratify_goal(gid, Actor.HUMAN)
    assert ctrl.graph.node(gid)["status"] == "ACTIVE"
    assert events_of(ctrl, Ev.GOAL_RATIFIED.value)[-1].actor == "human"


def test_human_edit_carries_human_identity(ctrl_env):
    ctrl, _ = ctrl_env
    with pytest.raises(PermissionError):
        ctrl.human_edit_node("boots", {"importance": 0.5}, Actor.SYSTEM)
    ctrl.human_edit_node("boots", {"importance": 0.42}, Actor.HUMAN)
    assert ctrl.graph.node("boots")["props"]["importance"] == 0.42
    assert events_of(ctrl, Ev.HUMAN_EDIT.value)[-1].actor == "human"
