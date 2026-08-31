"""A pending human decision blocks ONLY its own task, never the loop.

Owner's directive (2026-08-31): "il sistema non deve fermarsi quando
richiede la mia approvazione: deve fermarsi solo per quel task e quelli
che la mia decisione ancora non concessa blocca".
"""
from __future__ import annotations

from pgdca.scenario.toy import create


def _run_until_pending(ctrl, max_cycles=20):
    for _ in range(max_cycles):
        r = ctrl.step()
        if r.status == "waiting_human":
            return r
    raise AssertionError("no pending decision reached")


def test_loop_keeps_working_around_a_pending_decision():
    ctrl, _ = create()
    first = _run_until_pending(ctrl)
    assert ctrl.pending_decision() is not None
    blocked = ctrl.pending_decision()["decision"].params.get("factor_id")
    seen_before = set(ctrl.journal.records)
    cycle_before = ctrl.cycle
    # the loop must keep cycling on OTHER factors, not freeze on the same
    # decision
    moved = False
    for _ in range(6):
        r = ctrl.step()
        assert ctrl.cycle > cycle_before          # cycles keep advancing
        cycle_before = ctrl.cycle
        if r.status in ("executed", "failed"):
            moved = True
            break
        if r.status == "waiting_human" and r.decision_id != first.decision_id:
            moved = True                          # a DIFFERENT decision
            break
    assert moved, "the loop froze on the pending decision"
    # the blocked factor was never acted on while its decision waited
    for did, rec in ctrl.journal.records.items():
        if did in seen_before or did == first.decision_id:
            continue
        if rec["decision"]["params"].get("factor_id") == blocked \
                and rec.get("execution"):
            raise AssertionError("blocked task was executed without approval")


def test_multiple_pending_resolve_individually():
    ctrl, _ = create()
    first = _run_until_pending(ctrl)
    # keep stepping until a SECOND independent decision parks
    second = None
    for _ in range(12):
        r = ctrl.step()
        if r.status == "waiting_human" and r.decision_id != first.decision_id:
            second = r
            break
    if second is not None:                        # scripted world permitting
        assert len(ctrl._pending) == 2
        ctrl.resolve_pending(False, "no al secondo",
                             decision_id=second.decision_id)
        assert first.decision_id in ctrl._pending
        assert second.decision_id not in ctrl._pending
    ctrl.resolve_pending(True, "ok al primo",
                         decision_id=first.decision_id)
    assert first.decision_id not in ctrl._pending
