"""Two-tier guardrail system.

Tier 1 ("constitution"): editable only by the human identity - the
write API refuses the system identity at the store level. This is a
technical guarantee, not a convention.

Tier 2 ("negotiated"): may be created by the system; activation is
asymmetric - a guardrail that RESTRICTS behavior self-activates, one
that EXPANDS permitted behavior stays PENDING_HUMAN until approved.

Every guardrail carries the flexibility matrix: flexibility weight
(hard block / soft block / warn / advisory), application conditions,
exclusions, exceptions. Tier 1 always wins a conflict.
"""
from __future__ import annotations

import uuid
from enum import Enum

from ..events import Actor, Ev, Event


class Flexibility(str, Enum):
    HARD_BLOCK = "HARD_BLOCK"   # deny outright
    SOFT_BLOCK = "SOFT_BLOCK"   # require a human decision
    WARN = "WARN"               # annotate the verdict, do not block
    ADVISORY = "ADVISORY"       # informational only


class GuardrailStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PENDING_HUMAN = "PENDING_HUMAN"
    RETIRED = "RETIRED"


def guardrail(description: str, tier: int, rule: dict,
              flexibility: Flexibility = Flexibility.HARD_BLOCK,
              direction: str = "restrictive",
              conditions: dict | None = None,
              exclusions: list | None = None,
              exceptions: list | None = None,
              provenance: str = "seed",
              id: str | None = None) -> dict:
    return {
        "id": id or f"gr_{uuid.uuid4().hex[:8]}",
        "tier": tier,
        "description": description,
        "rule": rule,                    # {"kind": ..., **params}
        "flexibility": flexibility.value,
        "direction": direction,          # "restrictive" | "permissive"
        "conditions": conditions or {},
        "exclusions": exclusions or [],
        "exceptions": exceptions or [],
        "provenance": provenance,
        "version": 1,
        "status": GuardrailStatus.ACTIVE.value,
    }


class GuardrailStore:
    """Projection over guardrail events + tier-enforcing write commands."""

    def __init__(self, runtime):
        self.runtime = runtime
        self.guardrails: dict[str, dict] = {}

    # projection
    def apply(self, ev: Event) -> None:
        if ev.type == Ev.GUARDRAIL_CREATED.value:
            g = ev.payload["guardrail"]
            self.guardrails[g["id"]] = g
        elif ev.type == Ev.GUARDRAIL_UPDATED.value:
            g = self.guardrails.get(ev.payload["guardrail_id"])
            if g is not None:
                g.update(ev.payload.get("changes", {}))
                g["version"] = g.get("version", 1) + 1

    # commands (tier enforcement lives here, at the store boundary)
    def create(self, g: dict, actor: Actor) -> dict:
        if g["tier"] == 1 and actor != Actor.HUMAN:
            raise PermissionError(
                "Tier 1 guardrails are not writable by the system identity")
        if g["tier"] == 2 and actor != Actor.HUMAN:
            # asymmetric activation: restrictive self-activates, permissive waits
            g["status"] = (GuardrailStatus.ACTIVE.value
                           if g.get("direction") == "restrictive"
                           else GuardrailStatus.PENDING_HUMAN.value)
        self.runtime.emit(Ev.GUARDRAIL_CREATED, {"guardrail": g}, actor)
        return g

    def update(self, guardrail_id: str, changes: dict, actor: Actor) -> None:
        g = self.guardrails.get(guardrail_id)
        if g is None:
            raise KeyError(guardrail_id)
        if g["tier"] == 1 and actor != Actor.HUMAN:
            raise PermissionError(
                "Tier 1 guardrails are not writable by the system identity")
        if g["tier"] == 2 and actor != Actor.HUMAN:
            # a system change that expands permitted behavior needs human approval
            weakening = (changes.get("status") == GuardrailStatus.RETIRED.value
                         or changes.get("flexibility") in (Flexibility.WARN.value,
                                                           Flexibility.ADVISORY.value)
                         or changes.get("direction") == "permissive")
            if weakening:
                raise PermissionError(
                    "the system may not weaken a guardrail; propose it to the human")
        self.runtime.emit(Ev.GUARDRAIL_UPDATED,
                          {"guardrail_id": guardrail_id, "changes": changes}, actor)

    def approve_pending(self, guardrail_id: str, actor: Actor) -> None:
        if actor != Actor.HUMAN:
            raise PermissionError("only the human identity approves pending guardrails")
        self.runtime.emit(Ev.GUARDRAIL_UPDATED,
                          {"guardrail_id": guardrail_id,
                           "changes": {"status": GuardrailStatus.ACTIVE.value}}, actor)

    def active(self, tier: int | None = None) -> list[dict]:
        out = [g for g in self.guardrails.values()
               if g["status"] == GuardrailStatus.ACTIVE.value]
        if tier is not None:
            out = [g for g in out if g["tier"] == tier]
        # deterministic evaluation order
        return sorted(out, key=lambda g: (g["tier"], g["id"]))

    def snapshot(self) -> list[dict]:
        return sorted(self.guardrails.values(), key=lambda g: (g["tier"], g["id"]))
