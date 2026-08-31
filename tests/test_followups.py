"""Scheduled verifications: real-time follow-ups with snooze.

Owner's flow: "after 5 days: did the boots arrive? -> ask the human;
yes -> closed; no -> snooze to tomorrow". Wall-clock is injected in
tests, so nothing here depends on the real date.
"""
from __future__ import annotations

from pgdca.events import Actor
from pgdca.scenario.toy import create

T0 = 1_700_000_000.0
DAY = 86400.0


def test_due_followup_opens_a_question_thread_and_never_refires():
    ctrl, _ = create()
    f = ctrl.followups.schedule("sono arrivati gli scarponi?", 5,
                                node_id="boots", actor=Actor.HUMAN,
                                now_ts=T0)
    assert f["status"] == "scheduled" and f["node_id"] == "boots"
    assert ctrl.followups.check(now_ts=T0 + 4 * DAY) == []   # non ancora
    opened = ctrl.followups.check(now_ts=T0 + 5 * DAY + 1)
    assert len(opened) == 1
    assert "sono arrivati gli scarponi?" in opened[0]["messages"][0]["text"]
    assert opened[0]["subject"] == {"kind": "node", "id": "boots"}
    # idempotente: gia' chiesta, non rispunta
    assert ctrl.followups.check(now_ts=T0 + 6 * DAY) == []


def test_confirmed_resolution_closes_the_verification():
    ctrl, _ = create()
    f = ctrl.followups.schedule("consegna avvenuta?", 1, actor=Actor.HUMAN,
                                now_ts=T0)
    th = ctrl.followups.check(now_ts=T0 + 2 * DAY)[0]
    ctrl.resolve_deliberation(th["id"], "confirmed", note="arrivati, ok",
                              actor=Actor.HUMAN)
    assert ctrl.followup_store.items[f["id"]]["status"] == "done"


def test_snooze_reschedules_and_refires_later():
    ctrl, _ = create()
    f = ctrl.followups.schedule("sono arrivati?", 1, actor=Actor.HUMAN,
                                now_ts=T0)
    th = ctrl.followups.check(now_ts=T0 + DAY + 1)[0]
    ctrl.resolve_deliberation(th["id"], "modified", note="non ancora, domani",
                              changes={"snooze_days": 1}, actor=Actor.HUMAN)
    assert ctrl.followup_store.items[f["id"]]["status"] == "scheduled"
    # lo snooze riparte dal momento REALE della risposta ("domani"):
    # il giorno dopo (tempo vero) la domanda torna
    import time
    assert ctrl.followups.check(now_ts=time.time() + 0.5 * DAY) == []
    assert len(ctrl.followups.check(now_ts=time.time() + 2 * DAY)) == 1


def test_recovery_replays_followup_state(tmp_path):
    db = str(tmp_path / "fu.db")
    ctrl1, _ = create(db_path=db)
    ctrl1.followups.schedule("verifica dopo recovery", 3, actor=Actor.HUMAN,
                             now_ts=T0)
    ctrl2, _ = create(db_path=db)
    snap = ctrl2.followup_store.snapshot()
    assert len(snap) == 1 and snap[0]["question"] == "verifica dopo recovery"
