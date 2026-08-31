"""Scheduled verifications ("chrono tasks"): time-based follow-ups.

The owner's expected flow, verbatim (2026-08-31): "dopo 5 giorni sono
arrivati gli scarponi? -> controlla, verifica con l'umano. Sì -> chiuso.
No -> contatta il venditore o rimanda a domani."

A follow-up is an event-sourced record with a REAL (wall-clock) due
date. Every cycle the engine checks what is due and opens a consensus
thread with the question; the human closes it in chat:
- confirmed  -> done (the verification passed);
- modified with {"snooze_days": N} -> postponed by N days;
- cancelled  -> dropped.
Recovery replays the events, so triggered follow-ups never re-fire.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

from .events import Actor, Ev, Event

DAY_S = 86400.0


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(
        timespec="seconds")


class FollowupProjection:
    def __init__(self):
        self.items: dict[str, dict] = {}
        self.order: list[str] = []

    def apply(self, ev: Event) -> None:
        t, p = ev.type, ev.payload
        if t == Ev.FOLLOWUP_SCHEDULED.value:
            f = dict(p["followup"])
            if f["id"] not in self.items:
                self.order.append(f["id"])
            else:
                f = {**self.items[f["id"]], **f}     # snooze re-schedules
            f["status"] = "scheduled"
            self.items[f["id"]] = f
        elif t == Ev.FOLLOWUP_TRIGGERED.value:
            f = self.items.get(p.get("id", ""))
            if f is not None:
                f["status"] = "asked"
                f["thread_id"] = p.get("thread_id")
        elif t == Ev.FOLLOWUP_RESOLVED.value:
            f = self.items.get(p.get("id", ""))
            if f is not None:
                f["status"] = p.get("outcome", "done")

    def snapshot(self) -> list[dict]:
        return [dict(self.items[i]) for i in self.order]

    def due(self, now_ts: float) -> list[dict]:
        return [f for i in self.order
                for f in [self.items[i]]
                if f["status"] == "scheduled" and f["due_ts"] <= now_ts]


class FollowupEngine:
    def __init__(self, runtime, projection: FollowupProjection,
                 deliberation, graph):
        self.runtime = runtime
        self.projection = projection
        self.deliberation = deliberation
        self.graph = graph

    def schedule(self, question: str, due_in_days: float,
                 node_id: str = "", actor: Actor = Actor.HUMAN,
                 now_ts: float | None = None) -> dict:
        if not question.strip():
            raise ValueError("la verifica ha bisogno di una domanda")
        if node_id and self.graph.node(node_id) is None:
            raise KeyError(node_id)
        now = time.time() if now_ts is None else now_ts
        due = now + float(due_in_days) * DAY_S
        f = {"id": self.runtime.next_id("fu"), "question": question.strip(),
             "node_id": node_id, "due_ts": due, "due_at": _iso(due),
             "created_at": _iso(now)}
        self.runtime.emit(Ev.FOLLOWUP_SCHEDULED, {"followup": f}, actor)
        return self.projection.items[f["id"]]

    def snooze(self, fid: str, days: float, actor: Actor,
               now_ts: float | None = None) -> dict:
        f = self.projection.items.get(fid)
        if f is None:
            raise KeyError(fid)
        now = time.time() if now_ts is None else now_ts
        due = now + float(days) * DAY_S
        self.runtime.emit(Ev.FOLLOWUP_SCHEDULED, {"followup": {
            "id": fid, "question": f["question"], "node_id": f["node_id"],
            "due_ts": due, "due_at": _iso(due)}}, actor)
        return self.projection.items[fid]

    def resolve(self, fid: str, outcome: str, actor: Actor) -> None:
        if fid in self.projection.items:
            self.runtime.emit(Ev.FOLLOWUP_RESOLVED,
                              {"id": fid, "outcome": outcome}, actor)

    def check(self, now_ts: float | None = None) -> list[dict]:
        """Open a consensus thread for every due verification. Idempotent:
        triggered items leave the 'scheduled' state (event-sourced)."""
        now = time.time() if now_ts is None else now_ts
        opened = []
        for f in self.projection.due(now):
            subject = ({"kind": "node", "id": f["node_id"]}
                       if f["node_id"] and self.graph.node(f["node_id"])
                       else None)
            th = self.deliberation.open_system(
                f"Verifica programmata (scadenza {f['due_at']}): "
                f"{f['question']} Com'è andata? Rispondi in chat, poi: "
                f"confermato = verificata e chiusa; per rimandare risolvi "
                f"come modificato con {{\"snooze_days\": N}}; annullato = "
                f"lascia perdere.",
                {"checkpoint": "followup", "followup_id": f["id"],
                 "node_id": f["node_id"], "cycle": self.runtime.cycle},
                subject=subject)
            self.runtime.emit(Ev.FOLLOWUP_TRIGGERED,
                              {"id": f["id"], "thread_id": th["id"]},
                              Actor.SYSTEM)
            opened.append(th)
        return opened
