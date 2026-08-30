"""Deliberation: in-progress human-AI co-decision (spec: Deliberation
component, escalation-as-thread).

The human can open a discussion thread on any decision, graph node,
strategy branch, guardrail or contradiction at any time; the system
answers from reconstructed evidence (journal rationale, graph state,
branch state) through the LLM gateway - the packet is deterministic,
the wording is generative. The system opens threads of its own on
escalations. A thread's outcome - confirmed / modified / cancelled -
is decided by the human only, becomes an event, and can carry effects
(a node edit, a revocation with compensation, a strategy replan) that
run through the same channels as any other command. Resolved
dissent feeds the self-model, so contested decision classes surface
as advisories on future verdicts.
"""
from __future__ import annotations

from ..config import Config
from ..events import Actor, Ev, Event

SUBJECT_KINDS = ("decision", "node", "strategy", "guardrail",
                 "contradiction", "escalation")


class DeliberationProjection:
    def __init__(self):
        self.threads: dict[str, dict] = {}
        self.order: list[str] = []
        self.by_subject: dict[tuple[str, str], list[str]] = {}

    def apply(self, ev: Event) -> None:
        t, p = ev.type, ev.payload
        if t == Ev.DELIBERATION_OPENED.value:
            th = p.get("thread")
            if not isinstance(th, dict) or "id" not in th:
                return  # pre-Phase-4 shallow payloads carry no thread
            self.threads[th["id"]] = th
            self.order.append(th["id"])
            s = th.get("subject", {})
            self.by_subject.setdefault(
                (s.get("kind", "?"), s.get("id", "?")), []).append(th["id"])
        elif t == Ev.DELIBERATION_MESSAGE.value:
            th = self.threads.get(p.get("thread_id", ""))
            if th is not None:
                th["messages"].append(p["message"])
        elif t == Ev.DELIBERATION_RESOLVED.value:
            th = self.threads.get(p.get("thread_id", ""))
            if th is not None:
                th["status"] = "RESOLVED"
                th["resolution"] = p.get("resolution")

    # ----------------------------------------------------------- queries
    def open_threads(self) -> list[dict]:
        return [self.threads[t] for t in self.order
                if self.threads[t]["status"] == "OPEN"]

    def for_subject(self, kind: str, subject_id: str) -> list[dict]:
        return [self.threads[t]
                for t in self.by_subject.get((kind, subject_id), [])]

    def snapshot(self) -> list[dict]:
        return [self.threads[t] for t in self.order]


class DeliberationEngine:
    """Thread mechanics + evidence packets + generative answers.

    Resolution *effects* (edits, revocations, replans) are applied by
    the controller, which owns those channels; the engine records the
    resolution."""

    def __init__(self, runtime, projection: DeliberationProjection, gateway,
                 journal, graph, strategies, guardrails, evidence_store,
                 config: Config | None = None):
        self.runtime = runtime
        self.projection = projection
        self.gateway = gateway
        self.journal = journal
        self.graph = graph
        self.strategies = strategies
        self.guardrails = guardrails
        self.evidence_store = evidence_store
        self.config = config or Config()

    # ------------------------------------------------------------- open
    def open(self, subject_kind: str, subject_id: str, question: str,
             actor: Actor) -> dict:
        if actor != Actor.HUMAN:
            raise PermissionError(
                "discussion threads on subjects are opened by the human; "
                "the system opens threads only through escalation")
        if subject_kind not in SUBJECT_KINDS:
            raise KeyError(f"unknown subject kind '{subject_kind}'")
        evidence = self._evidence(subject_kind, subject_id)
        tid = self.runtime.next_id("del")
        thread = {
            "id": tid,
            "subject": {"kind": subject_kind, "id": subject_id},
            "status": "OPEN", "opened_by": actor.value,
            "cycle": self.runtime.cycle,
            "messages": [{"author": actor.value, "text": question}],
            "resolution": None,
        }
        self.runtime.emit(Ev.DELIBERATION_OPENED, {"thread": thread}, actor)
        self._answer(tid, question, evidence)
        return self.projection.threads[tid]

    def open_system(self, reason: str, packet: dict) -> dict:
        """An escalation packet becomes a discussion thread: the system
        states its blocker and waits; no generative call is needed - the
        packet is the message (replay stays LLM-free on this path)."""
        tid = self.runtime.next_id("del")
        thread = {
            "id": tid,
            "subject": {"kind": "escalation", "id": tid},
            "status": "OPEN", "opened_by": Actor.SYSTEM.value,
            "cycle": self.runtime.cycle,
            "messages": [{"author": Actor.SYSTEM.value,
                          "text": f"Escalation: {reason}",
                          "packet": packet}],
            "resolution": None,
        }
        self.runtime.emit(Ev.DELIBERATION_OPENED, {"thread": thread},
                          Actor.SYSTEM)
        return self.projection.threads[tid]

    # ------------------------------------------------------------ reply
    def reply(self, thread_id: str, text: str, actor: Actor) -> dict:
        if actor != Actor.HUMAN:
            raise PermissionError("thread replies carry the human identity; "
                                  "the system's answers are generated in turn")
        th = self.projection.threads.get(thread_id)
        if th is None:
            raise KeyError(thread_id)
        if th["status"] != "OPEN":
            raise ValueError(f"thread {thread_id} is already resolved")
        self.runtime.emit(Ev.DELIBERATION_MESSAGE,
                          {"thread_id": thread_id,
                           "message": {"author": actor.value, "text": text}},
                          actor)
        s = th["subject"]
        evidence = self._evidence(s["kind"], s["id"])
        self._answer(thread_id, text, evidence)
        return self.projection.threads[thread_id]

    def _answer(self, thread_id: str, question: str, evidence: dict) -> None:
        th = self.projection.threads[thread_id]
        resp = self.gateway.ask("deliberate", {
            "subject": th["subject"],
            "question": question,
            "evidence": evidence,
            "history": th["messages"][-self.config.deliberation_history_window:],
        })
        message = {"author": Actor.SYSTEM.value, "text": resp.summary}
        suggestions = [{"params": h.params, "rationale": h.rationale}
                       for h in resp.hypotheses
                       if h.action_name == "suggest_edit"]
        if suggestions:
            message["suggestions"] = suggestions
        self.runtime.emit(Ev.DELIBERATION_MESSAGE,
                          {"thread_id": thread_id, "message": message},
                          Actor.SYSTEM)

    # ---------------------------------------------------------- resolve
    def record_resolution(self, thread_id: str, resolution: dict,
                          actor: Actor) -> dict:
        if actor != Actor.HUMAN:
            raise PermissionError("deliberation outcomes are decided by "
                                  "the human")
        th = self.projection.threads.get(thread_id)
        if th is None:
            raise KeyError(thread_id)
        if th["status"] != "OPEN":
            raise ValueError(f"thread {thread_id} is already resolved")
        self.runtime.emit(Ev.DELIBERATION_RESOLVED,
                          {"thread_id": thread_id, "resolution": resolution},
                          actor)
        return self.projection.threads[thread_id]

    # --------------------------------------------------------- evidence
    def _evidence(self, kind: str, subject_id: str) -> dict:
        """Deterministic evidence packet reconstructed from projections.
        Raises KeyError when the subject does not exist."""
        if kind == "decision":
            r = self.journal.rationale(subject_id)
            if r is None:
                raise KeyError(subject_id)
            return r
        if kind == "node":
            n = self.graph.node(subject_id)
            if n is None:
                raise KeyError(subject_id)
            decisions = []
            for did in self.journal.node_index.get(subject_id, [])[-5:]:
                rec = self.journal.records[did]
                ex = rec.get("execution") or {}
                decisions.append({"decision_id": did,
                                  "action": rec["decision"]["action_name"],
                                  "status": ex.get("status", "not executed")})
            return {"node": n,
                    "goal_effects": self.graph.goal_effects(subject_id),
                    "decisions": decisions}
        if kind == "strategy":
            b = self.strategies.branches.get(subject_id)
            if b is None:
                raise KeyError(subject_id)
            return b
        if kind == "guardrail":
            g = next((g for g in self.guardrails.snapshot()
                      if g["id"] == subject_id), None)
            if g is None:
                raise KeyError(subject_id)
            return g
        if kind == "contradiction":
            c = self.evidence_store.contradictions.get(subject_id)
            if c is None:
                raise KeyError(subject_id)
            return c
        if kind == "escalation":
            for th in self.projection.for_subject("escalation", subject_id):
                first = th["messages"][0] if th["messages"] else {}
                return dict(first.get("packet") or {},
                            reason=first.get("text", ""))
            raise KeyError(subject_id)
        raise KeyError(kind)
