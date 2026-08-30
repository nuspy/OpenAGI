"""Evidence: claims, provenance and contradiction management (spec:
Contradiction Management, Provenance).

Claims are never silently overwritten: a conflict becomes an explicit
contradiction with both sides, their provenance, and a resolution
status. Provenance ranks: observed evidence outranks an external claim
(auto-resolution); two external claims stay UNRESOLVED for the human.
"""
from __future__ import annotations

from ..events import Actor, Ev, Event

RESOLUTIONS = ("UNRESOLVED", "RESOLVED_A", "RESOLVED_B",
               "CONTEXT_DEPENDENT", "OBSOLETE")


class EvidenceProjection:
    def __init__(self):
        self.claims: list[dict] = []
        self.contradictions: dict[str, dict] = {}

    def apply(self, ev: Event) -> None:
        t, p = ev.type, ev.payload
        if t == Ev.CLAIM_RECORDED.value:
            self.claims.append(dict(p, ts=ev.ts))
        elif t == Ev.CONTRADICTION_DETECTED.value:
            self.contradictions[p["id"]] = dict(p, ts=ev.ts)
        elif t == Ev.CONTRADICTION_UPDATED.value:
            c = self.contradictions.get(p["contradiction_id"])
            if c is not None:
                c.update(p.get("changes", {}))

    def claims_for(self, subject: str, attribute: str,
                   trust: str | None = None) -> list[dict]:
        return [c for c in self.claims
                if c["subject"] == subject and c["attribute"] == attribute
                and (trust is None or c.get("trust") == trust)]

    def has_claim(self, subject: str, attribute: str, value, source: str) -> bool:
        return any(c["subject"] == subject and c["attribute"] == attribute
                   and c["value"] == value and c["source"] == source
                   for c in self.claims)

    def snapshot(self) -> dict:
        return {"claims": list(self.claims),
                "contradictions": sorted(self.contradictions.values(),
                                         key=lambda c: c["id"])}


class EvidenceManager:
    def __init__(self, runtime, projection: EvidenceProjection):
        self.runtime = runtime
        self.projection = projection

    def record_claim(self, subject: str, attribute: str, value, source: str,
                     trust: str) -> None:
        if self.projection.has_claim(subject, attribute, value, source):
            return
        self.runtime.emit(Ev.CLAIM_RECORDED,
                          {"subject": subject, "attribute": attribute,
                           "value": value, "source": source, "trust": trust},
                          Actor.SYSTEM)

    def check_observation(self, subject: str, attribute: str, observed_value,
                          source: str) -> list[dict]:
        """An observation contradicting standing external claims produces
        explicit contradictions, auto-resolved in favor of the observation
        (observed provenance outranks external claims)."""
        found = []
        for claim in self.projection.claims_for(subject, attribute,
                                                trust="external"):
            if claim.get("contradicted"):
                continue
            try:
                differs = abs(float(claim["value"]) - float(observed_value)) > 1e-9
            except (TypeError, ValueError):
                differs = claim["value"] != observed_value
            if not differs:
                continue
            cid = self.runtime.next_id("contra")
            payload = {
                "id": cid, "subject": subject, "attribute": attribute,
                "claim_a": {"value": claim["value"], "source": claim["source"],
                            "trust": "external"},
                "claim_b": {"value": observed_value, "source": source,
                            "trust": "observed"},
                "status": "RESOLVED_B",
                "note": "observed evidence outranks the external claim",
            }
            self.runtime.emit(Ev.CONTRADICTION_DETECTED, payload, Actor.SYSTEM)
            claim["contradicted"] = True
            found.append(payload)
        return found

    def resolve(self, contradiction_id: str, status: str, actor: Actor,
                note: str = "") -> None:
        if actor != Actor.HUMAN:
            raise PermissionError("contradictions are resolved by the human")
        if status not in RESOLUTIONS:
            raise ValueError(f"unknown resolution '{status}'")
        self.runtime.emit(Ev.CONTRADICTION_UPDATED,
                          {"contradiction_id": contradiction_id,
                           "changes": {"status": status, "note": note}},
                          actor)
