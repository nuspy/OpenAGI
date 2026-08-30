"""Event store: the single source of truth.

Port + SQLite adapter. The default first storage profile is a single
relational instance (spec: Recommended Storage Architecture); the port
keeps the adapter substitutable (PostgreSQL in production profiles).
"""
from __future__ import annotations

import json
import sqlite3
import threading
from typing import Iterable, Protocol

from .events import Event


class EventStorePort(Protocol):
    def append(self, type: str, ts: str, actor: str, cycle: int | None, payload: dict) -> Event: ...
    def read(self, after_seq: int = 0) -> list[Event]: ...
    def last_seq(self) -> int: ...


class SqliteEventStore:
    """Append-only event log on SQLite (file or in-memory)."""

    def __init__(self, path: str = ":memory:"):
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.Lock()
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS events ("
            " seq INTEGER PRIMARY KEY AUTOINCREMENT,"
            " type TEXT NOT NULL,"
            " ts TEXT NOT NULL,"
            " actor TEXT NOT NULL,"
            " cycle INTEGER,"
            " payload TEXT NOT NULL)"
        )
        self._conn.commit()

    def append(self, type: str, ts: str, actor: str, cycle: int | None, payload: dict) -> Event:
        blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO events (type, ts, actor, cycle, payload) VALUES (?, ?, ?, ?, ?)",
                (type, ts, actor, cycle, blob),
            )
            self._conn.commit()
            seq = cur.lastrowid
        return Event(seq=seq, type=type, ts=ts, actor=actor, cycle=cycle, payload=payload)

    def read(self, after_seq: int = 0) -> list[Event]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT seq, type, ts, actor, cycle, payload FROM events WHERE seq > ? ORDER BY seq",
                (after_seq,),
            ).fetchall()
        return [
            Event(seq=r[0], type=r[1], ts=r[2], actor=r[3], cycle=r[4], payload=json.loads(r[5]))
            for r in rows
        ]

    def last_seq(self) -> int:
        with self._lock:
            row = self._conn.execute("SELECT COALESCE(MAX(seq), 0) FROM events").fetchone()
        return int(row[0])


def conformance_check(store: EventStorePort) -> list[str]:
    """Port conformance suite: any adapter must pass before use."""
    problems: list[str] = []
    e1 = store.append("CONFORMANCE", "1970-01-01T00:00:00Z", "system", None, {"k": "v"})
    if not isinstance(e1.seq, int) or e1.seq <= 0:
        problems.append("append must return a positive integer seq")
    e2 = store.append("CONFORMANCE", "1970-01-01T00:00:01Z", "system", 1, {"k": 2})
    if e2.seq <= e1.seq:
        problems.append("seq must be strictly increasing")
    got = store.read(after_seq=e1.seq)
    if not any(ev.seq == e2.seq and ev.payload == {"k": 2} for ev in got):
        problems.append("read(after_seq) must return later events with intact payloads")
    if store.last_seq() < e2.seq:
        problems.append("last_seq must reflect the latest append")
    return problems
