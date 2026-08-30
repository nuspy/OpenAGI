"""Event store, projections and rebuild."""
from __future__ import annotations

from pgdca.events import Actor, Ev
from pgdca.graph import GraphProjection
from pgdca.runtime import DeterministicClock, Runtime, rebuild
from pgdca.store import SqliteEventStore, conformance_check


def test_event_store_conformance():
    assert conformance_check(SqliteEventStore()) == []


def test_emit_dispatches_and_persists():
    rt = Runtime(SqliteEventStore(), DeterministicClock())
    g = rt.register(GraphProjection())
    rt.emit(Ev.NODE_ADDED, {"node": {"id": "n1", "kind": "FACTOR", "label": "x",
                                     "status": "ACTIVE", "review_interval": 3,
                                     "props": {}}}, Actor.HUMAN)
    assert g.node("n1") is not None
    evs = rt.events()
    assert len(evs) == 1 and evs[0].actor == "human"


def test_projections_rebuild_from_log():
    rt = Runtime(SqliteEventStore(), DeterministicClock())
    g = rt.register(GraphProjection())
    rt.emit(Ev.NODE_ADDED, {"node": {"id": "n1", "kind": "FACTOR", "label": "x",
                                     "status": "ACTIVE", "review_interval": 3,
                                     "props": {"importance": 0.5}}}, Actor.HUMAN)
    rt.emit(Ev.NODE_UPDATED, {"node_id": "n1", "props": {"importance": 0.9}},
            Actor.SYSTEM)
    fresh = GraphProjection()
    rebuild(rt.store, [fresh])
    assert fresh.node("n1")["props"]["importance"] == 0.9
    assert fresh.snapshot() == g.snapshot()


def test_deterministic_ids_and_clock():
    rt1 = Runtime(SqliteEventStore(), DeterministicClock())
    rt2 = Runtime(SqliteEventStore(), DeterministicClock())
    assert [rt1.next_id("x") for _ in range(3)] == [rt2.next_id("x") for _ in range(3)]
    e1 = rt1.emit(Ev.CYCLE_STARTED, {}, Actor.SYSTEM)
    e2 = rt2.emit(Ev.CYCLE_STARTED, {}, Actor.SYSTEM)
    assert e1.ts == e2.ts
