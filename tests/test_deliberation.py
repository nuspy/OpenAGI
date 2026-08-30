"""Phase 4: human-AI co-decision threads (M27) - evidence-grounded
answers, binding outcomes, escalation-as-thread, dissent advisories."""
from __future__ import annotations

import pytest

from pgdca.events import Actor, Ev
from pgdca.scenario.toy import ToyEnvironment, create
from tests.conftest import drive, events_of


def _decision_of(ctrl, factor_id, action="purchase"):
    return next(r for r in ctrl.journal.records.values()
                if r["decision"]["params"].get("factor_id") == factor_id
                and r["decision"]["action_name"] == action)


# ---------------------------------------------------------------- threads
def test_thread_answers_from_decision_evidence(ctrl_env):
    ctrl, _ = ctrl_env
    drive(ctrl)
    rec = _decision_of(ctrl, "boots")
    th = ctrl.open_deliberation("decision", rec["decision_id"],
                                "why did you buy the boots?")
    assert th["status"] == "OPEN" and th["opened_by"] == "human"
    assert [m["author"] for m in th["messages"]] == ["human", "system"]
    answer = th["messages"][1]["text"]
    assert "boots" in answer and "verdict" in answer
    assert "Ranked alternatives" in answer
    assert events_of(ctrl, Ev.DELIBERATION_OPENED.value,
                     Ev.DELIBERATION_MESSAGE.value)

    th2 = ctrl.reply_deliberation(th["id"], "and the counterfactual?")
    assert len(th2["messages"]) == 4
    assert th2["messages"][3]["author"] == "system"


def test_only_the_human_opens_replies_and_resolves(ctrl_env):
    ctrl, _ = ctrl_env
    drive(ctrl)
    with pytest.raises(PermissionError):
        ctrl.open_deliberation("node", "boots", "q", actor=Actor.SYSTEM)
    th = ctrl.open_deliberation("node", "boots", "why?")
    with pytest.raises(PermissionError):
        ctrl.reply_deliberation(th["id"], "sneaky", actor=Actor.SYSTEM)
    with pytest.raises(PermissionError):
        ctrl.resolve_deliberation(th["id"], "confirmed", actor=Actor.SYSTEM)
    ctrl.resolve_deliberation(th["id"], "confirmed", "ok")
    with pytest.raises(ValueError):
        ctrl.reply_deliberation(th["id"], "too late")


def test_unknown_subject_raises(ctrl_env):
    ctrl, _ = ctrl_env
    with pytest.raises(KeyError):
        ctrl.open_deliberation("decision", "dec_999", "?")
    with pytest.raises(KeyError):
        ctrl.open_deliberation("nonsense", "x", "?")


# ---------------------------------------------------------------- outcomes
def test_modified_outcome_applies_node_edit_with_human_provenance(ctrl_env):
    ctrl, _ = ctrl_env
    drive(ctrl)
    th = ctrl.open_deliberation("node", "bars",
                                "let's set importance to 0.4 for bars")
    sugg = th["messages"][1].get("suggestions")
    assert sugg and sugg[0]["params"]["props"] == {"importance": 0.4}
    ctrl.resolve_deliberation(th["id"], "modified", "agreed",
                              changes=sugg[0]["params"])
    assert ctrl.graph.node("bars")["props"]["importance"] == 0.4
    edits = events_of(ctrl, Ev.HUMAN_EDIT.value)
    assert any(e.payload.get("node_id") == "bars" for e in edits)
    res = ctrl.deliberations.threads[th["id"]]["resolution"]
    assert res["effects"][0]["type"] == "node_edited"


def test_cancelling_pending_decision_denies_it(ctrl_env):
    ctrl, _ = ctrl_env
    for _ in range(10):
        r = ctrl.run(10)[-1]
        if r.status == "waiting_human":
            break
    pend_id = ctrl.pending_decision()["decision"].id
    th = ctrl.open_deliberation("decision", pend_id, "is this worth it?")
    ctrl.resolve_deliberation(th["id"], "cancelled", "not convinced")
    assert ctrl.pending_decision() is None
    res = ctrl.deliberations.threads[th["id"]]["resolution"]
    assert {"type": "pending_denied"} in res["effects"]
    assert ctrl.budgets.snapshot()["money"]["spent"] == 0.0


def test_cancelling_executed_decision_compensates(ctrl_env):
    ctrl, env = ctrl_env
    for _ in range(10):
        r = ctrl.run(10)[-1]
        if r.status == "waiting_human":
            break
    ctrl.resolve_pending(True, "approve boots")
    rec = _decision_of(ctrl, "boots")
    th = ctrl.open_deliberation("decision", rec["decision_id"],
                                "I changed my mind about the boots")
    ctrl.resolve_deliberation(th["id"], "cancelled", "revoke it")
    res = ctrl.deliberations.threads[th["id"]]["resolution"]
    assert {"type": "revoked", "compensated": True} in res["effects"]
    assert ctrl.budgets.snapshot()["money"]["spent"] == 0.0
    assert env.refunds


def test_cancelling_active_strategy_defers_and_replans(ctrl_env):
    ctrl, _ = ctrl_env
    ctrl.step()   # plans and selects a branch
    active = next(b for b in ctrl.strategies.snapshot()
                  if b["status"] == "ACTIVE")
    th = ctrl.open_deliberation("strategy", active["id"],
                                "I don't like this ordering")
    assert active["label"] in th["messages"][1]["text"]
    ctrl.resolve_deliberation(th["id"], "cancelled", "replan please")
    assert ctrl.strategies.branches[active["id"]]["status"] == "DEFERRED"
    drive(ctrl)   # a replanned branch carries the scenario to completion
    assert any(b["status"] == "SUCCESSFUL" for b in ctrl.strategies.snapshot())


# ------------------------------------------------------------- escalation
def test_escalation_opens_system_thread():
    env = ToyEnvironment()
    ctrl, _ = create(env=env)
    # an adapter with no ideas: open targets + zero hypotheses = escalation
    ctrl.gateway.adapter = type("Empty", (), {
        "generate": staticmethod(lambda req: {
            "schema": "cognitive_response/1",
            "role": req.get("role", "?"), "summary": "nothing",
            "hypotheses": []})})()
    r = ctrl.step()
    assert r.status == "escalated"
    ths = ctrl.deliberations.open_threads()
    assert ths and ths[0]["opened_by"] == "system"
    assert ths[0]["subject"]["kind"] == "escalation"
    assert "no viable hypotheses" in ths[0]["messages"][0]["text"]
    # the human can answer in place and close the thread
    th = ctrl.reply_deliberation(ths[0]["id"], "understood, I'll add funds")
    assert th["messages"][-1]["author"] == "system"
    ctrl.resolve_deliberation(ths[0]["id"], "confirmed", "ack")
    assert ctrl.deliberations.threads[ths[0]["id"]]["status"] == "RESOLVED"


# ------------------------------------------------------ dissent advisories
def test_dissent_feeds_future_verdict_advisories():
    ctrl, env = create()
    for _ in range(10):
        r = ctrl.run(10)[-1]
        if r.status == "waiting_human":
            break
    ctrl.resolve_pending(True, "approve boots")
    rec = _decision_of(ctrl, "boots")
    th = ctrl.open_deliberation("decision", rec["decision_id"], "revoke")
    ctrl.resolve_deliberation(th["id"], "cancelled", "changed my mind")
    sig = ctrl._decision_signature(rec["decision_id"])
    assert ctrl.self_model.recurrence(sig)["dissent"] == 1
    assert "contested" in (ctrl.self_model.dissent_advisory(sig) or "")

    # a fresh run over the same store: the next boots-like decision carries
    # the dissent advisory on its verdict
    drive(ctrl)
    boots2 = [r for r in ctrl.journal.records.values()
              if r["decision"]["params"].get("factor_id") == "boots"
              and r["decision"]["action_name"] == "purchase"
              and r.get("verdict")]
    assert any("[advisory]" in x and "contested" in x
               for r in boots2 for x in r["verdict"]["reasons"])


def test_threads_survive_recovery(tmp_path):
    db = str(tmp_path / "delib.db")
    ctrl, _ = create(db_path=db)
    drive(ctrl)
    th = ctrl.open_deliberation("node", "boots", "why?")
    del ctrl
    ctrl2, _ = create(db_path=db)
    th2 = ctrl2.deliberations.threads[th["id"]]
    assert th2["status"] == "OPEN"
    assert [m["author"] for m in th2["messages"]] == ["human", "system"]
    # id counters recovered: a new thread gets a fresh id, and resolution works
    th3 = ctrl2.open_deliberation("node", "helmet", "and this?")
    assert th3["id"] != th["id"]
    ctrl2.resolve_deliberation(th["id"], "confirmed", "ok after restart")
    assert ctrl2.deliberations.threads[th["id"]]["status"] == "RESOLVED"
