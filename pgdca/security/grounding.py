"""Grounding check (M30): a RAG-style anti-hallucination layer inside
the existing guardrail system.

A deterministic local knowledge store holds grounded facts from two
sources: observations the system itself made (research results are
auto-indexed - the world is the best ground truth) and documents the
human adds (KNOWLEDGE_ADDED, human-only). Retrieval is lexical
token-overlap - dependency-free and deterministic; an embedding-based
retriever can replace it behind the same interface in local deployment.

The check itself is a guardrail rule kind (`ground_check`), so it is
optional and carries the full flexibility matrix like every other
guardrail: HARD_BLOCK / SOFT_BLOCK / WARN / ADVISORY, conditions,
exclusions, exceptions, Tier 1 or Tier 2. A decision whose claimed
values contradict grounded facts - the advert's fake price against the
observed market price - triggers it deterministically, with no LLM in
the loop.
"""
from __future__ import annotations

import re

from ..events import Actor, Ev, Event

_TOKEN_RE = re.compile(r"[a-z0-9_.]+")


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


class GroundingStore:
    """Projection: grounded facts + lexical retrieval."""

    def __init__(self):
        self.docs: dict[str, dict] = {}
        self.order: list[str] = []
        # (factor_id, attribute) -> latest grounded value
        self.values: dict[tuple[str, str], dict] = {}

    def apply(self, ev: Event) -> None:
        t, p = ev.type, ev.payload
        if t == Ev.OBSERVATION_RECEIVED.value:
            obs = p.get("observation") or {}
            fid = obs.get("factor_id")
            if fid and "unit_cost" in obs:
                self._index(
                    doc_id=f"obs_{ev.seq}",
                    text=(f"observed: {fid} unit_cost {obs['unit_cost']} "
                          f"(source {obs.get('source', 'observation')})"),
                    meta={"factor_id": fid, "attribute": "unit_cost",
                          "value": obs["unit_cost"],
                          "source": obs.get("source", "observation")})
        elif t == Ev.KNOWLEDGE_ADDED.value:
            self._index(p["id"], p.get("text", ""), p.get("meta") or {})

    def _index(self, doc_id: str, text: str, meta: dict) -> None:
        self.docs[doc_id] = {"id": doc_id, "text": text, "meta": meta,
                             "tokens": _tokens(text)}
        self.order.append(doc_id)
        fid, attr = meta.get("factor_id"), meta.get("attribute")
        if fid and attr and "value" in meta:
            self.values[(fid, attr)] = {"value": meta["value"],
                                        "doc_id": doc_id,
                                        "source": meta.get("source", "human")}

    # ----------------------------------------------------------- queries
    def grounded_value(self, factor_id: str, attribute: str) -> dict | None:
        return self.values.get((factor_id, attribute))

    def retrieve(self, query: str, k: int = 3) -> list[dict]:
        q = _tokens(query)
        scored = []
        for did in self.order:
            d = self.docs[did]
            score = len(q & d["tokens"])
            if score > 0:
                scored.append((score, did))
        scored.sort(key=lambda x: (-x[0], x[1]))
        return [{"id": did, "score": s,
                 "text": self.docs[did]["text"],
                 "meta": self.docs[did]["meta"]}
                for s, did in scored[:k]]

    def snapshot(self) -> list[dict]:
        return [{"id": d["id"], "text": d["text"], "meta": d["meta"]}
                for d in (self.docs[i] for i in self.order)]


def add_knowledge(runtime, text: str, meta: dict | None, actor: Actor) -> str:
    """Curated knowledge is human-only; the system's own path into the
    store is real observation, never self-asserted facts."""
    if actor != Actor.HUMAN:
        raise PermissionError("knowledge documents are added by the human; "
                              "the system grounds itself through observation")
    kid = runtime.next_id("kb")
    runtime.emit(Ev.KNOWLEDGE_ADDED,
                 {"id": kid, "text": text, "meta": meta or {}}, actor)
    return kid


def ground_check(rule: dict, decision, grounding: GroundingStore
                 ) -> tuple[bool, str]:
    """Guardrail rule: claimed values must not contradict grounded facts;
    optionally, claims must have grounding evidence at all."""
    if grounding is None:
        return False, ""
    fid = decision.params.get("factor_id")
    if not fid:
        return False, ""
    tolerance = float(rule.get("tolerance", 0.15))
    for attr in rule.get("attributes", ["unit_cost"]):
        claimed = decision.params.get(attr)
        if claimed is None:
            continue
        g = grounding.grounded_value(fid, attr)
        if g is None:
            if rule.get("require_evidence"):
                return True, (f"claim {attr}={claimed} for '{fid}' has no "
                              f"grounding evidence (observation or curated "
                              f"knowledge)")
            continue
        gv = float(g["value"])
        if abs(float(claimed) - gv) > tolerance * max(abs(gv), 1e-9):
            return True, (f"ungrounded claim: {attr}={claimed} for '{fid}' "
                          f"contradicts grounded value {gv} "
                          f"(source {g['source']})")
    return False, ""
