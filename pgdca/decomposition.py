"""Autonomous target decomposition with human consensus.

The owner's expectation, verbatim (2026-08-31): "reach the mountain
summit -> own climbing boots -> we have or need to buy? (question to
the human) -> branch A: buy (find best buys, discuss until consensus,
purchase) / branch B: we have (verify quality)". A target the graph
cannot act on must not sit inert: the system proposes a breakdown and
ASKS, the human decides, the graph grows.

Mechanics (all existing channels, no new trust rules):
- trigger: an ACTIVE TARGET/SUB_TARGET with nothing feeding it (no
  incoming edges) and no decomposition thread yet;
- the gateway role "decompose" proposes sub-targets and QUESTIONS for
  the owner (e.g. "do you already own climbing boots?"), each option
  mapping to a different branch;
- the proposal becomes a deliberation thread (M27): nothing is woven
  without the human's resolution - confirming weaves the proposed
  branch, modifying weaves the edited one, cancelling leaves the graph
  untouched;
- weaving = SUB_TARGET nodes + SUPPORT edges with human provenance,
  through the same events as M31 integration.
"""
from __future__ import annotations

from .config import Config
from .domain import NodeKind, NodeStatus, RelType, ValidationStatus, edge, node
from .events import Actor, Ev

DECOMPOSABLE = (NodeKind.TARGET, NodeKind.SUB_TARGET)


class DecompositionEngine:
    def __init__(self, runtime, gateway, graph, deliberation,
                 config: Config | None = None, budgets=None):
        self.runtime = runtime
        self.gateway = gateway
        self.graph = graph
        self.deliberation = deliberation
        self.budgets = budgets
        self.config = config or Config()

    # ---------------------------------------------------------- triggers
    def _already_asked(self, target_id: str) -> bool:
        for th in self.deliberation.projection.for_subject("node", target_id):
            first = th["messages"][0] if th["messages"] else {}
            if (first.get("packet") or {}).get("checkpoint") == "decomposition":
                return True
        return False

    def candidates(self) -> list[dict]:
        out = []
        for t in self.graph.by_kind(*DECOMPOSABLE, status=NodeStatus.ACTIVE):
            if self.graph.in_edges(t["id"]):
                continue          # something already feeds it
            if self._already_asked(t["id"]):
                continue
            out.append(t)
        out.sort(key=lambda t: (-float(t["props"].get("priority", 0.5)),
                                t["id"]))
        return out

    # -------------------------------------------------------------- step
    def step(self) -> list[dict]:
        """At most N decompositions per cycle; returns the opened threads."""
        if not self.config.decomposition_enabled:
            return []
        opened = []
        for t in self.candidates()[:self.config.decomposition_max_per_cycle]:
            proposal = self.propose(t)
            if not proposal["subtargets"] and not proposal["questions"]:
                continue          # nothing worth the owner's attention
            opened.append(self._open_thread(t, proposal))
        return opened

    def propose(self, t: dict, conversation: list | None = None) -> dict:
        summary = {
            "goals": [{"id": g["id"], "label": g["label"]}
                      for g in sorted(self.graph.active_goals(),
                                      key=lambda x: x["id"])],
            "budget": ({"limit": self.budgets.limit("money"),
                        "remaining": self.budgets.remaining("money")}
                       if self.budgets else {}),
        }
        resp = self.gateway.ask("decompose", {
            "target": {"id": t["id"], "label": t["label"],
                       "priority": t["props"].get("priority", 0.5)},
            "graph": summary,
            # the owner's answers so far: refine the questions and scale the
            # breakdown to them (a small hill vs an 8000m peak)
            "conversation": conversation or [],
            "instruction":
                "You are scoping a goal WITH its owner before acting. FIRST "
                "understand it: what exactly they want, where and when, the "
                "constraints and conditions, and what they already have vs "
                "need. Use ask_owner (with explicit options where it forks) "
                "for every fact only the owner knows and that CHANGES the "
                "plan - e.g. the destination and its difficulty (a small "
                "hill differs enormously from an 8000m peak: gear, permits, "
                "training, guides, weather window), what equipment they own "
                "and its condition, fitness/experience, deadline, budget, "
                "companions. Do NOT assume defaults for these. THEN propose "
                "the concrete sub-targets, scaled to the answers, tagging "
                "each with params.branch when it belongs to one answer of a "
                "question. Ask before you break down; break down "
                "proportionately to the real situation.",
        })
        proposal = {"target_id": t["id"], "subtargets": [], "questions": [],
                    "notes": [r for r in resp.risks if isinstance(r, dict)]}
        for h in resp.hypotheses:
            p = h.params
            if h.action_name == "propose_subtarget" and p.get("label"):
                proposal["subtargets"].append(
                    {"label": str(p["label"]),
                     "priority": float(p.get("priority", 0.5)),
                     "branch": str(p.get("branch", "")),
                     "rationale": h.rationale})
            elif h.action_name == "ask_owner" and p.get("question"):
                proposal["questions"].append(
                    {"question": str(p["question"]),
                     "options": [str(o) for o in (p.get("options") or [])]})
        return proposal

    def _open_thread(self, t: dict, proposal: dict) -> dict:
        qs = "; ".join(
            q["question"] + (f" [{' / '.join(q['options'])}]"
                             if q["options"] else "")
            for q in proposal["questions"])
        branches = sorted({s["branch"] for s in proposal["subtargets"]
                           if s["branch"]})
        reason = (f"breakdown of target '{t['label']}': "
                  f"{len(proposal['subtargets'])} sub-target(s)"
                  + (f" in branches {', '.join(branches)}" if branches else "")
                  + (f". Question for you: {qs}" if qs else "")
                  + ". Reply to discuss; resolve to weave (confirmed = as "
                    "proposed; modified = pass {\"proposal\": {..., "
                    "\"branch\": \"<option>\"}} to weave one branch only).")
        return self.deliberation.open_system(
            reason,
            {"checkpoint": "decomposition", "node_id": t["id"],
             "proposal": proposal, "cycle": self.runtime.cycle},
            subject={"kind": "node", "id": t["id"]})

    def rescope_for_thread(self, thread_id: str, history: list) -> bool:
        """Re-scope a decomposition thread as the owner answers: refine the
        questions and the breakdown, post them, and carry the updated
        proposal so resolving weaves the CURRENT one. Returns True when it
        handled the reply (so the generic Q&A answer is skipped)."""
        th = self.deliberation.projection.threads.get(thread_id)
        if th is None:
            return False
        packet = next((m.get("packet") for m in reversed(th["messages"])
                       if (m.get("packet") or {}).get("checkpoint")
                       == "decomposition"), None)
        if not packet:
            return False
        t = self.graph.node(packet.get("node_id", ""))
        if t is None:
            return False
        convo = [{"author": m["author"], "text": m["text"]}
                 for m in history if m.get("text")]
        proposal = self.propose(t, conversation=convo)
        qs = "; ".join(
            q["question"] + (f" [{' / '.join(q['options'])}]"
                             if q["options"] else "")
            for q in proposal["questions"])
        text = ("Ho aggiornato in base a quello che mi hai detto. "
                + (f"Ancora qualche domanda: {qs} " if qs else "")
                + (f"Piano attuale: {len(proposal['subtargets'])} passo/i "
                   f"({', '.join(s['label'] for s in proposal['subtargets'])}). "
                   if proposal["subtargets"] else "")
                + "Rispondi ancora, oppure conferma per inserirli nel piano.")
        self.deliberation.post_system(thread_id, text,
                                      {"checkpoint": "decomposition",
                                       "node_id": t["id"], "proposal": proposal,
                                       "cycle": self.runtime.cycle})
        return True

    # ------------------------------------------------------------- weave
    def apply(self, proposal: dict, actor: Actor,
              branch: str = "") -> list[dict]:
        """Weave the agreed breakdown (called by the controller on the
        thread's human resolution). `branch` limits the weave to one
        answered branch; branchless sub-targets always apply."""
        parent = proposal.get("target_id", "")
        if self.graph.node(parent) is None:
            raise KeyError(parent)
        effects: list[dict] = []
        for s in proposal.get("subtargets", []):
            if branch and s.get("branch") and s["branch"] != branch:
                continue
            sid = self.runtime.next_id("tgt")
            self.runtime.emit(Ev.NODE_ADDED, {"node": node(
                sid, NodeKind.SUB_TARGET, s["label"],
                priority=float(s.get("priority", 0.5)),
                spawned_by=parent, branch=s.get("branch", ""))}, actor)
            self.runtime.emit(Ev.EDGE_ADDED, {"edge": edge(
                self.runtime.next_id("de"), sid, parent, RelType.SUPPORT,
                ValidationStatus.VALIDATED, f"decomposition_agreed:{parent}",
                importance=float(s.get("priority", 0.5)),
                confidence=0.9)}, actor)
            effects.append({"type": "subtarget_added", "id": sid,
                            "label": s["label"], "branch": s.get("branch", "")})
        return effects
