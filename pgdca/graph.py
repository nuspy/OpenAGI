"""Goal/factor graph projection with causal-propagation guardrails.

Derived entirely from graph events. Effect propagation is depth-bounded,
multiplies uncertainty along paths, and penalizes HYPOTHESIZED edges
(spec: Causal and Effect Propagation, propagation guardrails).
"""
from __future__ import annotations

from .config import Config
from .domain import (CHAIN_RELS, GOAL_KINDS, NEGATIVE_RELS, POSITIVE_RELS,
                     NodeKind, NodeStatus, RelType, ValidationStatus)
from .events import Ev, Event


class GraphProjection:
    def __init__(self, config: Config | None = None):
        self.config = config or Config()
        self.nodes: dict[str, dict] = {}
        self.edges: dict[str, dict] = {}
        self.dirty: set[str] = set()

    # ------------------------------------------------------------- events
    def apply(self, ev: Event) -> None:
        t, p = ev.type, ev.payload
        if t == Ev.NODE_ADDED.value:
            n = p["node"]
            self.nodes[n["id"]] = n
            self.dirty.add(n["id"])
        elif t in (Ev.NODE_UPDATED.value, Ev.HUMAN_EDIT.value) and "node_id" in p:
            n = self.nodes.get(p["node_id"])
            if n is None:
                return
            n["props"].update(p.get("props", {}))
            if "status" in p:
                n["status"] = p["status"]
            if "label" in p:
                n["label"] = p["label"]
            self.dirty.add(n["id"])
        elif t in (Ev.NODE_INVALIDATED.value, Ev.TARGET_INVALIDATED.value):
            n = self.nodes.get(p["node_id"])
            if n is not None:
                n["status"] = p.get("status", NodeStatus.INVALIDATED.value)
                self.dirty.add(n["id"])
        elif t == Ev.TARGET_COMPLETED.value:
            n = self.nodes.get(p["node_id"])
            if n is not None:
                n["status"] = NodeStatus.COMPLETED.value
                self.dirty.add(n["id"])
        elif t == Ev.TARGET_DEFERRED.value:
            n = self.nodes.get(p["node_id"])
            if n is not None:
                n["status"] = NodeStatus.DEFERRED.value
                if p.get("blocked_by"):    # exogenous blocker: reversible
                    n["props"]["deferred_by"] = p["blocked_by"]
                self.dirty.add(n["id"])
        elif t in (Ev.DIRECTIVE_ISSUED.value, Ev.FACT_RECORDED.value):
            n = p["node"]
            self.nodes[n["id"]] = n
            self.dirty.add(n["id"])
        elif t == Ev.EDGE_ADDED.value:
            e = p["edge"]
            e.setdefault("_cycle", ev.cycle or 0)   # for hygiene TTL
            self.edges[e["id"]] = e
            self.dirty.update((e["src"], e["dst"]))
        elif t == Ev.EDGE_UPDATED.value:
            e = self.edges.get(p["edge_id"])
            if e is None:
                return
            e["attrs"].update(p.get("attrs", {}))
            for k in ("validation_status", "validity_status"):
                if k in p:
                    e[k] = p[k]
            self.dirty.update((e["src"], e["dst"]))
        elif t == Ev.GOAL_PROPOSED.value:
            n = p["node"]
            n["status"] = NodeStatus.PROPOSED.value
            self.nodes[n["id"]] = n
            self.dirty.add(n["id"])
        elif t == Ev.GOAL_RATIFIED.value:
            n = self.nodes.get(p["node_id"])
            if n is not None:
                n["status"] = NodeStatus.ACTIVE.value
                self.dirty.add(n["id"])
        elif t == Ev.CYCLE_COMPLETED.value:
            pass  # dirty set is drained by the reconciler, not by cycles

    # ------------------------------------------------------------ queries
    def node(self, node_id: str) -> dict | None:
        return self.nodes.get(node_id)

    def out_edges(self, node_id: str, types: set[RelType] | None = None) -> list[dict]:
        tv = {t.value for t in types} if types else None
        return [e for e in self.edges.values()
                if e["src"] == node_id and e["validity_status"] == NodeStatus.ACTIVE.value
                and (tv is None or e["type"] in tv)]

    def in_edges(self, node_id: str, types: set[RelType] | None = None) -> list[dict]:
        tv = {t.value for t in types} if types else None
        return [e for e in self.edges.values()
                if e["dst"] == node_id and e["validity_status"] == NodeStatus.ACTIVE.value
                and (tv is None or e["type"] in tv)]

    def by_kind(self, *kinds: NodeKind, status: NodeStatus | None = None) -> list[dict]:
        kv = {k.value for k in kinds}
        out = [n for n in self.nodes.values() if n["kind"] in kv]
        if status is not None:
            out = [n for n in out if n["status"] == status.value]
        return out

    def active_goals(self) -> list[dict]:
        return [n for n in self.nodes.values()
                if n["kind"] in {k.value for k in GOAL_KINDS}
                and n["status"] == NodeStatus.ACTIVE.value]

    def open_targets(self) -> list[dict]:
        return self.by_kind(NodeKind.TARGET, NodeKind.SUB_TARGET, status=NodeStatus.ACTIVE)

    def substitutes_of(self, factor_id: str) -> list[str]:
        """Factors that can substitute `factor_id` (edge: sub -SUBSTITUTES-> factor)."""
        return [e["src"] for e in self.in_edges(factor_id, {RelType.SUBSTITUTES})]

    # ------------------------------------------- causal effect propagation
    def _edge_confidence(self, e: dict) -> float:
        conf = float(e["attrs"].get("confidence", 0.8))
        if e["validation_status"] == ValidationStatus.HYPOTHESIZED.value:
            conf *= self.config.hypothesized_edge_penalty
        return conf

    def goal_effects(self, factor_id: str, max_depth: int | None = None) -> dict[str, dict]:
        """Signed, confidence-weighted effects of a factor on active goals.

        Returns {goal_id: {"effect": signed strength, "confidence": path conf,
        "path": [edge ids], "unvalidated": bool}}. Depth-bounded; uncertainty
        multiplies along the path; HYPOTHESIZED edges are penalized.
        """
        depth = max_depth or self.config.max_propagation_depth
        goal_kinds = {k.value for k in GOAL_KINDS}
        results: dict[str, dict] = {}
        frontier = [(factor_id, 1.0, 1.0, [], False)]  # node, sign, conf, path, unvalidated
        for _ in range(depth):
            nxt = []
            for nid, sign, conf, path, unval in frontier:
                for e in self.out_edges(nid):
                    rt = e["type"]
                    econf = self._edge_confidence(e)
                    strength = float(e["attrs"].get("importance", 0.5))
                    e_unval = unval or e["validation_status"] == ValidationStatus.HYPOTHESIZED.value
                    if rt in {t.value for t in POSITIVE_RELS}:
                        s = sign
                    elif rt in {t.value for t in NEGATIVE_RELS}:
                        s = -sign
                    elif rt in {t.value for t in CHAIN_RELS}:
                        nxt.append((e["dst"], sign, conf * econf, path + [e["id"]], e_unval))
                        continue
                    else:
                        continue
                    dst = self.nodes.get(e["dst"])
                    if dst is None:
                        continue
                    if dst["kind"] in goal_kinds:
                        eff = s * strength
                        pconf = conf * econf
                        cur = results.get(dst["id"])
                        if cur is None or abs(eff) * pconf > abs(cur["effect"]) * cur["confidence"]:
                            results[dst["id"]] = {"effect": eff, "confidence": pconf,
                                                  "path": path + [e["id"]], "unvalidated": e_unval}
                    else:
                        nxt.append((e["dst"], s, conf * econf, path + [e["id"]], e_unval))
            frontier = nxt
            if not frontier:
                break
        return results

    def antagonisms(self, factor_id: str) -> list[dict]:
        """Goals this factor supports and goals it harms, when both exist."""
        eff = self.goal_effects(factor_id)
        pos = [g for g, d in eff.items() if d["effect"] > 0]
        neg = [g for g, d in eff.items() if d["effect"] < 0]
        if pos and neg:
            return [{"factor": factor_id, "supports": pos, "harms": neg}]
        return []

    def snapshot(self) -> dict:
        return {"nodes": list(self.nodes.values()), "edges": list(self.edges.values())}
