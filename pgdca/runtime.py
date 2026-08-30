"""Runtime: append events, dispatch to projections, rebuild for replay.

Projections are derived views rebuilt from the event log; workers and
the GUI never own state of their own (spec: Event Sourcing section).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Callable, Protocol

from .events import Actor, Ev, Event
from .store import EventStorePort


class Clock(Protocol):
    def now(self) -> str: ...


class DeterministicClock:
    """Logical clock: each tick advances one second from a fixed epoch.

    Guarantees byte-identical timestamps under deterministic replay.
    """

    def __init__(self, start: str = "2026-08-30T00:00:00+00:00"):
        self._t = datetime.fromisoformat(start)

    def now(self) -> str:
        self._t += timedelta(seconds=1)
        return self._t.isoformat()


class WallClock:
    def now(self) -> str:
        return datetime.now(timezone.utc).isoformat()


class Projection(Protocol):
    def apply(self, ev: Event) -> None: ...


class Runtime:
    def __init__(self, store: EventStorePort, clock: Clock | None = None):
        self.store = store
        self.clock = clock or DeterministicClock()
        self.projections: list[Projection] = []
        self.subscribers: list[Callable[[Event], None]] = []
        self.cycle: int | None = None
        self._id_counters: dict[str, int] = {}

    def next_id(self, prefix: str) -> str:
        """Deterministic id generator - identical ids under replay."""
        n = self._id_counters.get(prefix, 0) + 1
        self._id_counters[prefix] = n
        return f"{prefix}_{n}"

    def register(self, projection: Projection, catch_up: bool = True):
        """Attach a projection; optionally feed it the existing log."""
        if catch_up:
            for ev in self.store.read(0):
                projection.apply(ev)
        self.projections.append(projection)
        return projection

    def emit(self, type: Ev | str, payload: dict, actor: Actor | str = Actor.SYSTEM) -> Event:
        ev = self.store.append(
            type=str(type.value if isinstance(type, Ev) else type),
            ts=self.clock.now(),
            actor=str(actor.value if isinstance(actor, Actor) else actor),
            cycle=self.cycle,
            payload=payload,
        )
        for p in self.projections:
            p.apply(ev)
        for s in list(self.subscribers):
            s(ev)
        return ev

    def subscribe(self, fn: Callable[[Event], None]) -> None:
        self.subscribers.append(fn)

    def events(self, after_seq: int = 0) -> list[Event]:
        return self.store.read(after_seq)


def rebuild(store: EventStorePort, projections: list[Projection]) -> None:
    """Rebuild projections from scratch out of the event log.

    Used for recovery and for the deterministic-replay verification.
    """
    for ev in store.read(0):
        for p in projections:
            p.apply(ev)
