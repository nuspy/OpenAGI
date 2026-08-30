"""Phase 9 / M31-M32: exogenous directives and facts, integration with
consensus, reversible blocking, CRUD re-evaluation, change-set ops,
AI-initiated consultations, federation-ready origins."""
from __future__ import annotations

import pytest

from pgdca.arbitration import _goal_contribution
from pgdca.cognition.mock_llm import MockReviewerAdapter
from pgdca.domain import (NodeKind, NodeStatus, RelType, ValidationStatus,
                          edge, node)
from pgdca.events import Actor, Ev
from pgdca.scenario.toy import create
from tests.conftest import drive, events_of

H = Actor.HUMAN


def mini_world():
    """Two goals, one meeting target, a modest budget - the vacation
    stage."""
    ctrl, _ = create(build=False)
    rt = ctrl.runtime
    rt.emit(Ev.NODE_ADDED, {"node": node(
        "wellbeing", NodeKind.META_GOAL, "Long-term wellbeing",
        priority=0.9)}, H)
    rt.emit(Ev.NODE_ADDED, {"node": node(
        "career", NodeKind.PERSISTENT_GOAL, "Career growth",
        priority=0.7)}, H)
    rt.emit(Ev.NODE_ADDED, {"node": node(
        "t_meeting", NodeKind.TARGET, "Weekly meetings")}, H)
    ctrl.set_budget("money", 500.0, H)
    return ctrl


def integration_thread(ctrl, node_id):
    return ctrl._integration_thread(node_id)


# ------------------------------------------------------------------- CRUD
def test_directive_crud_events_and_thread():
    ctrl = mini_world()
    d = ctrl.exogenous.issue_directive(
        "Two weeks of vacation", "recharge properly", weight=0.8,
        horizon="short", directive_type="context")
    assert d["kind"] == "DIRECTIVE" and d["status"] == "PROPOSED"
    assert d["props"]["priority"] == 0.8
    assert d["props"]["origin"]["authority"] == "owner"
    assert events_of(ctrl, Ev.DIRECTIVE_ISSUED.value)
    assert events_of(ctrl, Ev.INTEGRATION_PROPOSED.value)
    th = integration_thread(ctrl, d["id"])
    assert th is not None and th["opened_by"] == "system"
    snap = ctrl.exogenous.snapshot()
    assert snap["directives"][0]["id"] == d["id"]

    with pytest.raises(PermissionError):
        ctrl.exogenous.update(d["id"], {"priority": 0.9}, Actor.SYSTEM)
    ctrl.exogenous.update(d["id"], {"priority": 0.9}, H)
    assert ctrl.graph.node(d["id"])["props"]["priority"] == 0.9
    assert events_of(ctrl, Ev.REEVALUATION_REQUESTED.value)
    assert d["id"] in ctrl.graph.dirty


# ------------------------------------------------- integration consensus
def _weave_vacation():
    ctrl = mini_world()
    d = ctrl.exogenous.issue_directive(
        "Vacation plan for wellbeing, avoid meetings",
        weight=0.8, directive_type="target")
    th = integration_thread(ctrl, d["id"])
    proposal = th["messages"][0]["packet"]["proposal"]
    assert any(e["dst"] == "wellbeing" and e["type"] == "SUPPORT"
               for e in proposal["edges"])
    assert any(e["dst"] == "t_meeting" and e["type"] == "BLOCK"
               for e in proposal["edges"])
    assert proposal["new_targets"] and proposal["deferrals"]
    assert proposal["conflicts"]          # blocking an active target is named

    ctrl.resolve_deliberation(th["id"], "confirmed", "va bene, si parte")
    assert ctrl.graph.node(d["id"])["status"] == "ACTIVE"
    applied = events_of(ctrl, Ev.INTEGRATION_APPLIED.value)[-1].payload
    assert applied["edges"] >= 2 and applied["targets"] == 1
    woven = [e for e in ctrl.graph.edges.values()
             if e["provenance"] == f"integration_agreed:{d['id']}"]
    assert woven and all(e["validation_status"] == "VALIDATED" for e in woven)
    # the meeting target is deferred by the vacation, reversibly
    tm = ctrl.graph.node("t_meeting")
    assert tm["status"] == "DEFERRED" and tm["props"]["deferred_by"] == d["id"]
    # the spawned plan subtarget is traceable to its directive
    plan = next(n for n in ctrl.graph.nodes.values()
                if n["props"].get("spawned_by") == d["id"])
    assert plan["kind"] == "TARGET" and plan["label"].startswith("Plan:")
    return ctrl, d, plan


def test_vacation_directive_weaves_on_consensus():
    _weave_vacation()


def test_woven_directive_weighs_in_arbitration():
    ctrl, d, plan = _weave_vacation()
    eff = ctrl.graph.goal_effects(plan["id"])
    assert d["id"] in eff and eff[d["id"]]["effect"] > 0
    total, _, detail = _goal_contribution(ctrl.graph, plan["id"], 0.9)
    assert total > 0 and d["id"] in detail


# ------------------------------------------------- reversible blocking
def test_block_edge_defers_and_retire_reactivates():
    ctrl = mini_world()
    d = ctrl.exogenous.issue_directive("Quiet period", weight=0.6)
    ctrl.resolve_deliberation(integration_thread(ctrl, d["id"])["id"],
                              "confirmed", "ok")
    ctrl.runtime.emit(Ev.EDGE_ADDED, {"edge": edge(
        "e_block_m", d["id"], "t_meeting", RelType.BLOCK,
        ValidationStatus.VALIDATED, "human", importance=0.8,
        confidence=0.9)}, H)
    ctrl.step()
    tm = ctrl.graph.node("t_meeting")
    assert tm["status"] == "DEFERRED" and tm["props"]["deferred_by"] == d["id"]

    out = ctrl.exogenous.retire(d["id"], H, "vacation over")
    assert "e_block_m" in out["edges_invalidated"]
    ctrl.step()
    assert ctrl.graph.node("t_meeting")["status"] == "ACTIVE"
    assert not ctrl.graph.node("t_meeting")["props"].get("deferred_by")


def test_retire_lists_orphans_for_review():
    ctrl, d, plan = _weave_vacation()
    out = ctrl.exogenous.retire(d["id"], H)
    assert plan["id"] in out["orphans"]
    orphan_th = next(t for t in ctrl.deliberations.open_threads()
                     if (t["messages"][0].get("packet") or {})
                     .get("checkpoint") == "orphan_review")
    assert plan["id"] in orphan_th["messages"][0]["text"]


# ---------------------------------------------------------------- facts
def test_fact_imposed_vs_opportunity():
    ctrl = mini_world()
    law = ctrl.exogenous.record_fact("New regulation on meetings",
                                     weight=0.6, mode="imposed")
    assert law["status"] == "ACTIVE"          # imposed facts are true on arrival
    assert integration_thread(ctrl, law["id"])  # the weaving is still discussed

    inh = ctrl.exogenous.record_fact(
        "Inheritance received, larger budget available",
        weight=0.7, mode="opportunity")
    assert inh["status"] == "PROPOSED"
    ctrl.accept_opportunity(inh["id"])
    assert ctrl.graph.node(inh["id"])["status"] == "ACTIVE"
    assert events_of(ctrl, Ev.INTEGRATION_APPLIED.value)

    nope = ctrl.exogenous.record_fact("Dubious offer", weight=0.4,
                                      mode="opportunity")
    ctrl.decline_opportunity(nope["id"])
    assert ctrl.graph.node(nope["id"])["status"] == "INVALIDATED"
    with pytest.raises(ValueError):
        ctrl.exogenous.record_fact("x", mode="whatever")


def test_auto_weave_below_threshold(ctrl_env):
    ctrl = mini_world()
    ctrl.update_config({"exogenous_auto_weave_below": 0.9}, H)
    d = ctrl.exogenous.issue_directive("Support wellbeing daily", weight=0.5)
    assert integration_thread(ctrl, d["id"]) is None      # no thread
    assert ctrl.graph.node(d["id"])["status"] == "ACTIVE"
    auto = [e for e in ctrl.graph.edges.values()
            if e["provenance"] == f"integration_auto:{d['id']}"]
    assert auto and all(e["validation_status"] == "HYPOTHESIZED"
                        for e in auto)


# ------------------------------------------------- federation readiness
def test_non_owner_origin_is_external_and_never_auto():
    ctrl = mini_world()
    ctrl.update_config({"exogenous_require_consensus": False}, H)
    peer = ctrl.exogenous.record_fact(
        "Colleague's AI reports shared unavailability", weight=0.6,
        mode="imposed", actor=Actor.ENVIRONMENT,
        origin={"source": "network", "authority": "peer",
                "instance": "ai-colleague"})
    assert peer["status"] == "PROPOSED"       # never active without the human
    assert integration_thread(ctrl, peer["id"]) is not None
    ingested = [e for e in events_of(ctrl, Ev.CONTENT_INGESTED.value)
                if e.payload.get("content_id") == f"exo_{peer['id']}"]
    assert ingested and ingested[0].payload["trust"] == "external"
    with pytest.raises(PermissionError):
        ctrl.exogenous.issue_directive("sneaky", actor=Actor.SYSTEM)


def test_integration_reviewed_when_checkpoint_enabled():
    ctrl, _ = create(build=False)
    ctrl.runtime.emit(Ev.NODE_ADDED, {"node": node(
        "wellbeing", NodeKind.META_GOAL, "Long-term wellbeing",
        priority=0.9)}, H)
    ctrl.set_budget("money", 500.0, H)
    matrix = dict(ctrl.config.review_matrix)
    matrix["integration"] = {"enabled": True, "max_rounds": 1,
                             "on_disagreement": "human"}
    ctrl.update_config({"review_matrix": matrix}, H)
    ctrl2 = mini_world()  # fresh, for the stubborn reviewer variant
    del ctrl2
    d = ctrl.exogenous.issue_directive("Support wellbeing", weight=0.7)
    th = integration_thread(ctrl, d["id"])
    assert th["messages"][0]["packet"]["review_outcome"] == "consensus"
    assert any(r["checkpoint"] == "integration"
               for r in ctrl.reviews.snapshot())


# --------------------------------------------------- change-set ops (M32)
def test_scenario_thread_and_changeset_ops():
    ctrl = mini_world()
    th = ctrl.open_deliberation("scenario", "overall",
                                "let's move the budget to 300")
    answer = th["messages"][1]
    assert "Scenario:" in answer["text"]
    sugg = answer.get("suggestions")
    assert sugg and sugg[0]["params"]["ops"][0]["op"] == "set_budget"

    ctrl.resolve_deliberation(th["id"], "modified", "agreed", changes=[
        {"op": "set_budget", "name": "money", "limit": 300},
        {"op": "new_fact", "label": "Company reorg announced",
         "weight": 0.5},
        {"op": "propose_goal", "kind": "PERSISTENT_GOAL",
         "label": "Learn sailing", "priority": 0.6, "ratify": True},
        {"op": "defer_target", "node_id": "t_meeting",
         "reason": "paused during replanning"},
    ])
    assert ctrl.budgets.limit("money") == 300.0
    assert any(n["kind"] == "FACT" and n["label"] == "Company reorg announced"
               for n in ctrl.graph.nodes.values())
    sail = next(n for n in ctrl.graph.nodes.values()
                if n["label"] == "Learn sailing")
    assert sail["status"] == "ACTIVE"          # proposed and ratified in one act
    assert ctrl.graph.node("t_meeting")["status"] == "DEFERRED"
    res = ctrl.deliberations.threads[th["id"]]["resolution"]
    assert len(res["effects"]) == 4
    with pytest.raises(ValueError):
        ctrl._apply_ops([{"op": "nonsense"}], H)


# ------------------------------------------------- consultations (M32)
def test_conflict_with_directive_opens_consultation(ctrl_env):
    ctrl, _ = ctrl_env
    d = ctrl.exogenous.issue_directive("Guard the diet discipline",
                                       weight=0.7)
    ctrl.resolve_deliberation(integration_thread(ctrl, d["id"])["id"],
                              "confirmed", "ok")
    ctrl.runtime.emit(Ev.EDGE_ADDED, {"edge": edge(
        "e_bars_dirv", "bars", d["id"], RelType.ANTAGONIZE,
        ValidationStatus.VALIDATED, "human", importance=0.6,
        confidence=0.9)}, H)
    drive(ctrl)
    cons = [t for t in ctrl.deliberations.snapshot()
            if (t["messages"][0].get("packet") or {})
            .get("checkpoint") == "consultation"]
    assert cons and d["id"] in cons[0]["messages"][0]["text"]


def test_periodic_consultation_is_config_gated(ctrl_env):
    ctrl, _ = ctrl_env
    drive(ctrl)
    assert not [t for t in ctrl.deliberations.snapshot()
                if (t["messages"][0].get("packet") or {})
                .get("checkpoint") == "consultation"]
    ctrl2, _ = create()
    ctrl2.update_config({"consultation_interval_cycles": 3}, H)
    drive(ctrl2)
    sync = [t for t in ctrl2.deliberations.snapshot()
            if "periodic sync" in t["messages"][0]["text"]]
    assert sync and "budget remaining" in sync[0]["messages"][0]["text"]


# ------------------------------------------------------------- recovery
def test_exogenous_survives_recovery(tmp_path):
    db = str(tmp_path / "exo.db")
    ctrl, _ = create(db_path=db)
    d = ctrl.exogenous.issue_directive("Support wellbeing", weight=0.7)
    ctrl.resolve_deliberation(integration_thread(ctrl, d["id"])["id"],
                              "confirmed", "ok")
    del ctrl
    ctrl2, _ = create(db_path=db)
    n = ctrl2.graph.node(d["id"])
    assert n is not None and n["status"] == "ACTIVE"
    d2 = ctrl2.exogenous.issue_directive("Another one", weight=0.4)
    assert d2["id"] != d["id"]                # id counters recovered
