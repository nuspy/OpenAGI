"""Persistent operation: recovery from an existing event store."""
from __future__ import annotations

from pgdca.events import Actor
from pgdca.scenario.toy import create
from tests.conftest import drive


def test_recovery_resumes_pending_decision_and_ids(tmp_path):
    db = str(tmp_path / "pgdca.db")
    ctrl1, _ = create(db_path=db)
    for _ in range(10):
        r = ctrl1.run(10)[-1]
        if r.status == "waiting_human":
            break
    assert ctrl1.pending_decision() is not None
    ids_before = set(ctrl1.journal.records)
    cycle_before = ctrl1.cycle
    del ctrl1  # "process restart"

    ctrl2, env2 = create(db_path=db)
    assert ctrl2.state.value == "WAITING_HUMAN"
    pend = ctrl2.pending_decision()
    assert pend is not None and pend["decision"].params["factor_id"] == "boots"
    assert ctrl2.cycle == cycle_before

    ctrl2.resolve_pending(True, "approved after restart")
    last = drive(ctrl2)
    assert last.status == "idle"
    # no id collisions across the restart: journal keys are decision ids
    assert ids_before <= set(ctrl2.journal.records)
    assert len(set(ctrl2.journal.order)) == len(ctrl2.journal.order)
    b = ctrl2.budgets.snapshot()["money"]
    assert b["spent"] <= b["limit"] == 500.0
    for tid in ("t_boots", "t_helmet", "t_snacks"):
        assert ctrl2.graph.node(tid)["status"] == "COMPLETED"


def test_recovery_honors_stop_until_human_resume(tmp_path):
    db = str(tmp_path / "pgdca2.db")
    ctrl1, _ = create(db_path=db)
    ctrl1.step()
    ctrl1.control("STOP", Actor.HUMAN)
    del ctrl1

    ctrl2, _ = create(db_path=db)
    assert ctrl2.state.value == "STOPPED"
    assert ctrl2.step().status == "stopped"
    ctrl2.control("RESUME", Actor.HUMAN)   # explicit human resume clears STOP
    r = ctrl2.step()
    assert r.status != "stopped" and ctrl2.cycle >= 2


def test_recovery_restores_denied_signatures(tmp_path):
    db = str(tmp_path / "pgdca3.db")
    ctrl1, _ = create(db_path=db)
    for _ in range(10):
        r = ctrl1.run(10)[-1]
        if r.status == "waiting_human":
            break
    ctrl1.resolve_pending(False, "denied before restart")  # deny the boots buy
    denied = set(ctrl1._denied_signatures)
    assert denied
    del ctrl1

    ctrl2, _ = create(db_path=db)
    assert denied <= ctrl2._denied_signatures
