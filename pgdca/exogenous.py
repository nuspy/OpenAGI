"""Exogenous inputs (M31): directives and facts entering the running loop.

A DIRECTIVE is a normative human decision issued mid-flight - a new
short/long-horizon target, an imposed limit or thing to avoid, a
context-modifying decision. It carries a weight (`priority`) and, once
woven, is a first-class propagation anchor: goal_effects, U(a),
antagonisms and critique consider it automatically among all existing
decision points (DIRECTIVE is in GOAL_KINDS).

A FACT is a descriptive scenario change - `imposed` (true regardless:
a new law, an inheritance received) or an `opportunity` the human
accepts or declines. It carries a weight (`importance`) and acts
through its typed edges plus the deterministic blocking rule in the
reconciler.

**Integration = consensus before weaving**: the gateway role
`integrate` proposes typed weighted edges against the existing graph,
new subtargets, deferrals, budget impacts and detected conflicts; the
proposal opens a system deliberation thread (M27) - optionally passing
cross-AI review first (M29 checkpoint "integration") - and applies only
when the human resolves it (confirmed/modified). Budget impacts are
never automatic (the M3 ratchet): they are listed for the human to
apply as change-set ops. Below `exogenous_auto_weave_below` weight the
edges self-apply as HYPOTHESIZED (the graph guardrails - penalty + TTL
- govern them) with no thread.

**CRUD with re-evaluation**: updates mark the subgraph dirty and emit
REEVALUATION_REQUESTED; retirement (event-sourced - never physical
deletion) invalidates every touching edge, lists integration-spawned
nodes in an orphan-review thread, and the reconciler reactivates the
targets this node was blocking.

**Federation-ready** (see docs/future_features.md): every node carries
an `origin` envelope {source, authority, instance}. Only
`authority: "owner"` (the local human) is trusted; anything else is
external content - CONTENT_INGESTED + taint, ground-check applicable,
consensus always required, never auto-active, never Tier 1. Future
superior/peer AI instances enter through this same channel with a
different envelope.
"""
from __future__ import annotations

from .config import Config
from .domain import (EXOGENOUS_KINDS, NodeKind, NodeStatus, RelType,
                     ValidationStatus, edge, node)
from .events import Actor, Ev

OWNER_ORIGIN = {"source": "human_gui", "authority": "owner",
                "instance": "local"}


class ExogenousManager:
    def __init__(self, runtime, graph, gateway, deliberation, reviewer,
                 budgets, config: Config | None = None):
        self.runtime = runtime
        self.graph = graph
        self.gateway = gateway
        self.deliberation = deliberation
        self.reviewer = reviewer
        self.budgets = budgets
        self.config = config or Config()

    # ------------------------------------------------------------ create
    def issue_directive(self, label: str, description: str = "",
                        weight: float = 0.6, horizon: str = "short",
                        directive_type: str = "context",
                        actor: Actor = Actor.HUMAN,
                        origin: dict | None = None) -> dict:
        origin = dict(origin or OWNER_ORIGIN)
        self._check_authority(actor, origin)
        nid = self.runtime.next_id("dirv")
        n = node(nid, NodeKind.DIRECTIVE, label,
                 status=NodeStatus.PROPOSED,
                 priority=float(weight), horizon=horizon,
                 directive_type=directive_type, description=description,
                 origin=origin)
        self._ingest_if_external(nid, label, description, origin)
        self.runtime.emit(Ev.DIRECTIVE_ISSUED, {"node": n}, actor)
        self._integrate(self.graph.node(nid), actor)
        return self.graph.node(nid)

    def record_fact(self, label: str, description: str = "",
                    weight: float = 0.5, mode: str = "imposed",
                    actor: Actor = Actor.HUMAN,
                    origin: dict | None = None) -> dict:
        if mode not in ("imposed", "opportunity"):
            raise ValueError(f"unknown fact mode '{mode}'")
        origin = dict(origin or OWNER_ORIGIN)
        self._check_authority(actor, origin)
        trusted = origin.get("authority") == "owner"
        # an imposed fact from the owner is true on arrival; its weaving
        # is still discussed. Opportunities - and anything not from the
        # owner - wait for the human.
        status = (NodeStatus.ACTIVE if (mode == "imposed" and trusted)
                  else NodeStatus.PROPOSED)
        nid = self.runtime.next_id("fact")
        n = node(nid, NodeKind.FACT, label, status=status,
                 importance=float(weight), mode=mode,
                 description=description, origin=origin)
        self._ingest_if_external(nid, label, description, origin)
        self.runtime.emit(Ev.FACT_RECORDED, {"node": n}, actor)
        self._integrate(self.graph.node(nid), actor)
        return self.graph.node(nid)

    def _check_authority(self, actor: Actor, origin: dict) -> None:
        if origin.get("authority") == "owner" and actor != Actor.HUMAN:
            raise PermissionError(
                "owner-authority exogenous inputs carry the human identity; "
                "non-owner sources must declare their own authority")

    def _ingest_if_external(self, nid: str, label: str, description: str,
                            origin: dict) -> None:
        """Trust rule, live today: a non-owner origin is external content
        - tainted, ground-checkable, never auto-trusted."""
        if origin.get("authority") == "owner":
            return
        self.runtime.emit(Ev.CONTENT_INGESTED,
                          {"content_id": f"exo_{nid}",
                           "text": f"{label}. {description}".strip(),
                           "trust": "external",
                           "source": f"{origin.get('authority', '?')}:"
                                     f"{origin.get('instance', '?')}"},
                          Actor.ENVIRONMENT)

    # ------------------------------------------------------- integration
    def _weight(self, n: dict) -> float:
        p = n["props"]
        return float(p.get("priority", p.get("importance", 0.5)))

    def _integrate(self, n: dict, actor: Actor) -> None:
        proposal = self.propose_integration(n)
        self.runtime.emit(Ev.INTEGRATION_PROPOSED,
                          {"node_id": n["id"], "proposal": proposal},
                          Actor.SYSTEM)
        review = self.reviewer.review(
            "integration", {"id": n["id"], "node": n, "proposal": proposal},
            {})
        trusted = (n["props"].get("origin") or {}).get("authority") == "owner"
        # opportunities always await the human; nothing non-owner ever
        # auto-weaves
        auto = (trusted
                and n["props"].get("mode") != "opportunity"
                and (not self.config.exogenous_require_consensus
                     or self._weight(n) < self.config.exogenous_auto_weave_below))
        if auto:
            self.apply_integration(n["id"], proposal, actor=Actor.SYSTEM,
                                   validated=False)
            return
        conflicts = "; ".join(c.get("reason", str(c))
                              for c in proposal.get("conflicts", [])) or "none"
        self.deliberation.open_system(
            f"integration of {n['kind'].lower()} {n['id']} ('{n['label']}', "
            f"weight {self._weight(n)}): {len(proposal['edges'])} relation(s), "
            f"{len(proposal['new_targets'])} new target(s), "
            f"{len(proposal['deferrals'])} deferral(s) proposed. "
            f"Conflicts: {conflicts}. Resolve to weave it into the graph; "
            f"budget impacts need explicit change-set ops.",
            {"checkpoint": "integration", "node_id": n["id"],
             "proposal": proposal,
             "review_outcome": review.get("outcome"),
             "cycle": self.runtime.cycle})

    def propose_integration(self, n: dict) -> dict:
        """Ask the gateway to weave the node against the existing graph;
        parse the structured hypotheses into a proposal."""
        summary = {
            "goals": [{"id": g["id"], "label": g["label"],
                       "priority": g["props"].get("priority", 0.5)}
                      for g in sorted(self.graph.active_goals(),
                                      key=lambda x: x["id"])],
            "targets": [{"id": t["id"], "label": t["label"]}
                        for t in sorted(self.graph.open_targets(),
                                        key=lambda x: x["id"])],
            "factors": [{"id": f["id"], "label": f["label"]}
                        for f in sorted(self.graph.by_kind(NodeKind.FACTOR),
                                        key=lambda x: x["id"])],
            "budget": {"limit": self.budgets.limit("money"),
                       "remaining": self.budgets.remaining("money")},
        }
        resp = self.gateway.ask("integrate", {"node": n, "graph": summary})
        proposal = {"edges": [], "new_targets": [], "deferrals": [],
                    "budget_notes": [], "conflicts": list(resp.risks),
                    "questions": list(resp.missing_information)}
        for h in resp.hypotheses:
            p = h.params
            if h.action_name == "propose_edge" and p.get("src") and p.get("dst"):
                proposal["edges"].append(
                    {"src": p["src"], "dst": p["dst"],
                     "type": p.get("type", "SUPPORT"),
                     "importance": float(p.get("importance", 0.5)),
                     "confidence": float(p.get("confidence", 0.7)),
                     "rationale": h.rationale})
            elif h.action_name == "propose_target" and p.get("label"):
                proposal["new_targets"].append(
                    {"label": p["label"],
                     "priority": float(p.get("priority", 0.5)),
                     "rationale": h.rationale})
            elif h.action_name == "propose_deferral" and p.get("target_id"):
                proposal["deferrals"].append(
                    {"target_id": p["target_id"], "reason": h.rationale})
            elif h.action_name == "budget_note":
                proposal["budget_notes"].append(p.get("note", h.rationale))
        return proposal

    def apply_integration(self, node_id: str, proposal: dict,
                          actor: Actor = Actor.HUMAN,
                          validated: bool = True) -> dict:
        """Weave the agreed proposal: human confirmation makes the edges
        VALIDATED and ratifies the spawned targets; the auto path (below
        the weave threshold) stays HYPOTHESIZED under the graph
        guardrails. Returns a summary of what was applied."""
        n = self.graph.node(node_id)
        if n is None or n["kind"] not in {k.value for k in EXOGENOUS_KINDS}:
            raise KeyError(node_id)
        provenance = (f"integration_agreed:{node_id}" if validated
                      else f"integration_auto:{node_id}")
        vstatus = (ValidationStatus.VALIDATED if validated
                   else ValidationStatus.HYPOTHESIZED)
        applied = {"node_id": node_id, "edges": 0, "targets": 0,
                   "deferrals": 0, "mode": "agreed" if validated else "auto"}
        for e in proposal.get("edges", []):
            if self.graph.node(e["src"]) is None or self.graph.node(e["dst"]) is None:
                continue
            self.runtime.emit(Ev.EDGE_ADDED, {"edge": edge(
                self.runtime.next_id("ie"), e["src"], e["dst"],
                RelType(e.get("type", "SUPPORT")), vstatus, provenance,
                importance=float(e.get("importance", 0.5)),
                confidence=float(e.get("confidence", 0.7)))}, actor)
            applied["edges"] += 1
        for t in proposal.get("new_targets", []):
            tid = self.runtime.next_id("tgt")
            self.runtime.emit(Ev.NODE_ADDED, {"node": node(
                tid, NodeKind.TARGET, t["label"],
                priority=float(t.get("priority", 0.5)),
                spawned_by=node_id)}, actor)
            self.runtime.emit(Ev.EDGE_ADDED, {"edge": edge(
                self.runtime.next_id("ie"), tid, node_id, RelType.SUPPORT,
                vstatus, provenance,
                importance=float(t.get("priority", 0.5)),
                confidence=0.9)}, actor)
            applied["targets"] += 1
        for d in proposal.get("deferrals", []):
            if self.graph.node(d["target_id"]) is not None:
                self.runtime.emit(Ev.TARGET_DEFERRED,
                                  {"node_id": d["target_id"],
                                   "reason": d.get("reason", "") or
                                   f"integration of {node_id}",
                                   "blocked_by": node_id}, actor)
                applied["deferrals"] += 1
        if n["status"] != NodeStatus.ACTIVE.value:
            self.runtime.emit(Ev.NODE_UPDATED,
                              {"node_id": node_id,
                               "status": NodeStatus.ACTIVE.value, "props": {}},
                              actor)
        self.runtime.emit(Ev.INTEGRATION_APPLIED, applied, actor)
        return applied

    def reintegrate(self, node_id: str, actor: Actor) -> None:
        """Re-run the weaving analysis in a fresh thread (after edits)."""
        if actor != Actor.HUMAN:
            raise PermissionError("re-integration is requested by the human")
        n = self.graph.node(node_id)
        if n is None or n["kind"] not in {k.value for k in EXOGENOUS_KINDS}:
            raise KeyError(node_id)
        self._integrate(n, actor)

    # ------------------------------------------------- update and retire
    def update(self, node_id: str, props: dict, actor: Actor) -> None:
        """Weight/props edits re-evaluate the relations: the dirty
        subgraph is re-scored next cycle (event-driven reconciler)."""
        if actor != Actor.HUMAN:
            raise PermissionError("exogenous nodes are edited by the human")
        n = self.graph.node(node_id)
        if n is None or n["kind"] not in {k.value for k in EXOGENOUS_KINDS}:
            raise KeyError(node_id)
        self.runtime.emit(Ev.HUMAN_EDIT, {"node_id": node_id, "props": props},
                          actor)
        self.runtime.emit(Ev.REEVALUATION_REQUESTED,
                          {"node_id": node_id, "reason": "exogenous update"},
                          actor)

    def retire(self, node_id: str, actor: Actor, note: str = "") -> dict:
        """Event-sourced deletion: invalidate the node and every touching
        edge; integration-spawned nodes go to an orphan-review thread;
        the reconciler reactivates the targets this node was blocking."""
        if actor != Actor.HUMAN:
            raise PermissionError("exogenous nodes are retired by the human")
        n = self.graph.node(node_id)
        if n is None or n["kind"] not in {k.value for k in EXOGENOUS_KINDS}:
            raise KeyError(node_id)
        self.runtime.emit(Ev.NODE_INVALIDATED,
                          {"node_id": node_id,
                           "status": NodeStatus.INVALIDATED.value,
                           "reason": note or "retired by the human"}, actor)
        cascaded = []
        for e in list(self.graph.edges.values()):
            if (node_id in (e["src"], e["dst"])
                    and e["validity_status"] == NodeStatus.ACTIVE.value):
                self.runtime.emit(Ev.EDGE_UPDATED,
                                  {"edge_id": e["id"], "validity_status":
                                   NodeStatus.INVALIDATED.value}, actor)
                cascaded.append(e["id"])
        orphans = [m["id"] for m in self.graph.nodes.values()
                   if m["props"].get("spawned_by") == node_id
                   and m["status"] in (NodeStatus.ACTIVE.value,
                                       NodeStatus.PROPOSED.value,
                                       NodeStatus.DEFERRED.value)]
        if orphans:
            self.deliberation.open_system(
                f"orphan review: {n['kind'].lower()} {node_id} "
                f"('{n['label']}') was retired; it had spawned "
                f"{', '.join(orphans)}. Decide whether they stay or go "
                f"(retire them via change-set ops or node edits).",
                {"checkpoint": "orphan_review", "node_id": node_id,
                 "orphans": orphans, "cycle": self.runtime.cycle})
        self.runtime.emit(Ev.REEVALUATION_REQUESTED,
                          {"node_id": node_id, "reason": "exogenous retire"},
                          actor)
        return {"retired": node_id, "edges_invalidated": cascaded,
                "orphans": orphans}

    # ------------------------------------------------------ opportunities
    def snapshot(self) -> dict:
        def row(m):
            p = m["props"]
            return {"id": m["id"], "label": m["label"], "status": m["status"],
                    "weight": p.get("priority", p.get("importance", 0.5)),
                    "horizon": p.get("horizon"), "type": p.get("directive_type"),
                    "mode": p.get("mode"), "description": p.get("description", ""),
                    "origin": p.get("origin", {})}
        return {
            "directives": [row(m) for m in sorted(
                self.graph.by_kind(NodeKind.DIRECTIVE), key=lambda x: x["id"])],
            "facts": [row(m) for m in sorted(
                self.graph.by_kind(NodeKind.FACT), key=lambda x: x["id"])],
        }
