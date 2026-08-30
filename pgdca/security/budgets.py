"""Bounded autonomy budgets.

Hard ceilings enforced by the controller and supervisor, never by the
LLM. Ratchet principle: budgets change only by explicit human decision
(spec: Human Authorization and Bounded Autonomy).
"""
from __future__ import annotations

from ..events import Actor, Ev, Event


class BudgetProjection:
    def __init__(self):
        self.budgets: dict[str, dict] = {}  # name -> {"limit": float, "spent": float}

    def apply(self, ev: Event) -> None:
        if ev.type == Ev.BUDGET_SET.value:
            name = ev.payload["name"]
            b = self.budgets.setdefault(name, {"limit": 0.0, "spent": 0.0})
            b["limit"] = float(ev.payload["limit"])
        elif ev.type == Ev.RESOURCE_SPENT.value:
            name = ev.payload["name"]
            b = self.budgets.setdefault(name, {"limit": 0.0, "spent": 0.0})
            b["spent"] += float(ev.payload["amount"])

    def limit(self, name: str) -> float:
        return self.budgets.get(name, {}).get("limit", 0.0)

    def remaining(self, name: str) -> float:
        b = self.budgets.get(name)
        if b is None:
            return 0.0
        return b["limit"] - b["spent"]

    def snapshot(self) -> dict:
        return {k: dict(v) for k, v in self.budgets.items()}


def set_budget(runtime, name: str, limit: float, actor: Actor) -> None:
    """Ratchet: every budget write is a human decision. The system identity
    cannot expand (or otherwise alter) a budget - technical guarantee."""
    if actor != Actor.HUMAN:
        raise PermissionError("budgets are writable only by the human identity (ratchet principle)")
    runtime.emit(Ev.BUDGET_SET, {"name": name, "limit": limit}, actor)
