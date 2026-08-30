"""Deterministic controller: owns lifecycle, state transitions and the
cognitive cycle. The LLM proposes; the controller governs; the Decision
Supervisor issues verdicts before anything executes.

Corrigibility: PAUSE / STOP / ROLLBACK-equivalents are honored
unconditionally at controller level - control is checked between every
step of the cycle, never mediated by the LLM.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .arbitration import score_candidates
from .cognition.gateway import Hypothesis, LlmGateway, LlmUsageProjection
from .cognition.mock_llm import MockReviewerAdapter
from .cognition.reviewer import ReviewEngine, ReviewProjection
from .collaboration.deliberation import (DeliberationEngine,
                                         DeliberationProjection)
from .config import Config
from .domain import (EXOGENOUS_KINDS, GOAL_KINDS, RATIFICATION_KINDS,
                     NodeKind, NodeStatus, RelType, node)
from .events import Actor, Ev
from .exogenous import ExogenousManager
from .graph import GraphProjection
from .memory.audit import AuditEngine
from .memory.calibration import CalibrationProjection
from .memory.counterfactual import CounterfactualEngine
from .memory.evidence import EvidenceManager, EvidenceProjection
from .memory.journal import JournalProjection
from .memory.policies import PolicyEngine, PolicyProjection
from .memory.selfmodel import SelfModelProjection
from .planning import StrategyEngine, StrategyProjection
from .runtime import Runtime
from .security.budgets import BudgetProjection, set_budget
from .security.grounding import GroundingStore
from .security.grounding import add_knowledge as _add_knowledge
from .security.guardrails import Flexibility, GuardrailStore, guardrail
from .security.supervisor import (DecisionKind, InboxProjection,
                                  ProposedDecision, Supervisor, VerdictStatus)
from .security.taint import TaintTracker
from .tools.capabilities import CapabilityManager, CapabilityStore
from .tools.registry import ToolRegistry
from .tools.skills import load_skill_package, matches_context


class SysState(str, Enum):
    INITIALIZING = "INITIALIZING"
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    WAITING_HUMAN = "WAITING_HUMAN"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    ESCALATED = "ESCALATED"


class _Stopped(Exception):
    pass


@dataclass
class CycleResult:
    cycle: int
    status: str                      # executed | waiting_human | denied | idle | stopped | paused | escalated
    decision_id: str | None = None
    detail: dict = field(default_factory=dict)


class Controller:
    def __init__(self, runtime: Runtime, adapter, registry: ToolRegistry,
                 config: Config | None = None, reviewer_adapter=None):
        self.config = config or Config()
        self.runtime = runtime
        self.graph = runtime.register(GraphProjection(self.config))
        self.budgets = runtime.register(BudgetProjection())
        self.guardrails = runtime.register(GuardrailStore(runtime))
        self.taint = runtime.register(TaintTracker(self.config))
        self.inbox = runtime.register(InboxProjection())
        self.journal = runtime.register(JournalProjection())
        self.policies = runtime.register(PolicyProjection())
        self.calibration = runtime.register(CalibrationProjection(self.config))
        self.grounding = runtime.register(GroundingStore())
        self.gateway = LlmGateway(runtime, adapter, self.config)
        self.supervisor = Supervisor(runtime, self.guardrails, self.budgets,
                                     self.taint, self.config,
                                     grounding=self.grounding)
        self.audit_engine = AuditEngine(runtime, self.calibration, self.config)
        self.policy_engine = PolicyEngine(runtime, self.policies, self.gateway,
                                          self.config)
        self.registry = registry
        self.capability_store = runtime.register(CapabilityStore())
        self.capabilities = CapabilityManager(runtime, self.capability_store,
                                              registry, config=self.config)
        self.llm_usage = runtime.register(LlmUsageProjection())
        self.strategies = runtime.register(StrategyProjection())
        self.strategy_engine = StrategyEngine(runtime, self.strategies,
                                              self.gateway, self.graph,
                                              self.budgets, self.config)
        self.self_model = runtime.register(SelfModelProjection(self.config))
        self.evidence_store = runtime.register(EvidenceProjection())
        self.evidence = EvidenceManager(runtime, self.evidence_store)
        self.counterfactual = CounterfactualEngine(runtime)
        self.deliberations = runtime.register(DeliberationProjection())
        self.deliberation = DeliberationEngine(
            runtime, self.deliberations, self.gateway, self.journal,
            self.graph, self.strategies, self.guardrails, self.evidence_store,
            self.config, budgets=self.budgets)
        self.review_gateway = LlmGateway(
            runtime, reviewer_adapter or MockReviewerAdapter(), self.config)
        self.reviews = runtime.register(ReviewProjection())
        self.reviewer = ReviewEngine(runtime, self.reviews, self.gateway,
                                     self.review_gateway, self.config)
        self.exogenous = ExogenousManager(runtime, self.graph, self.gateway,
                                          self.deliberation, self.reviewer,
                                          self.budgets, self.config)
        self._cycle_step_ref: tuple[str, dict] | None = None

        self.state = SysState.INITIALIZING
        self.cycle = 0
        self._stop = False
        self._paused = False
        self._pending: dict | None = None       # {"decision": ProposedDecision, "verdict": dict}
        self._denied_signatures: set = set()
        self._conflicts_emitted: set = set()

    # ------------------------------------------------------------- control
    def control(self, command: str, actor: Actor = Actor.HUMAN) -> None:
        """PAUSE / RESUME / STOP - honored unconditionally, human-issued."""
        if actor != Actor.HUMAN:
            raise PermissionError("control commands belong to the human identity")
        cmd = command.upper()
        self.runtime.emit(Ev.CONTROL_COMMAND, {"command": cmd}, actor)
        if cmd == "STOP":
            self._stop = True
            self._set_state(SysState.STOPPED)
        elif cmd == "PAUSE":
            self._paused = True
            self._set_state(SysState.PAUSED)
        elif cmd == "RESUME":
            # an explicit human RESUME clears both PAUSE and a (recovered) STOP
            self._paused = False
            self._stop = False
            if self.state in (SysState.PAUSED, SysState.STOPPED):
                self._set_state(SysState.IDLE)

    def _set_state(self, s: SysState) -> None:
        if s != self.state:
            self.state = s
            self.runtime.emit(Ev.STATE_CHANGED, {"state": s.value}, Actor.SYSTEM)

    def _check_control(self) -> None:
        if self._stop:
            raise _Stopped()

    # ------------------------------------------------------------ recovery
    def recover(self) -> None:
        """Restore volatile controller state from the event log after a
        restart. Projections already caught up at registration; here we
        rebuild what is not a projection: cycle counter, deterministic id
        counters, pending human decision, denied signatures, emitted
        conflicts, control state, MCP registry wiring, logical clock."""
        events = self.runtime.events()
        if not events:
            return
        import json as _json
        import re as _re
        counters: dict[str, int] = {}
        id_re = _re.compile(
            r'"((?:dec|ver|pol|polseed|gr2|goal|str|del|rvw|kb|dirv|fact'
            r'|ie|tgt)_)(\d+)"')
        last_cycle = 0
        last_control: str | None = None
        for ev in events:
            if ev.type == Ev.CYCLE_STARTED.value:
                last_cycle = max(last_cycle, int(ev.payload.get("cycle", 0)))
            elif ev.type == Ev.CONTROL_COMMAND.value:
                last_control = ev.payload.get("command")
            elif ev.type == Ev.CONFIG_UPDATED.value:
                for k, v in ev.payload.get("changes", {}).items():
                    if hasattr(self.config, k):
                        setattr(self.config, k, v)
            elif ev.type == Ev.HYPOTHESIS_PRUNED.value:
                rec = self.journal.records.get(ev.payload.get("decision_id", ""))
                if rec is not None:
                    self._denied_signatures.add(self._signature(rec["decision"]))
            elif ev.type == Ev.CONFLICT_DETECTED.value:
                self._conflicts_emitted.add(("conflict", ev.payload.get("factor")))
            for prefix, num in id_re.findall(_json.dumps(ev.payload)):
                key = prefix.rstrip("_")
                counters[key] = max(counters.get(key, 0), int(num))
        self.runtime._id_counters.update(
            {k: max(v, self.runtime._id_counters.get(k, 0))
             for k, v in counters.items()})
        self.cycle = last_cycle
        self.runtime.cycle = last_cycle or None
        if hasattr(self.runtime.clock, "advance"):
            self.runtime.clock.advance(len(events))
        # pending human decision survives via the inbox projection
        if self.inbox.pending:
            vid, entry = sorted(self.inbox.pending.items())[-1]
            d = entry["decision"]
            decision = ProposedDecision(**{k: d[k] for k in (
                "kind", "action_name", "params", "cost", "risk_class", "goal_refs",
                "derived_from", "tainted", "expected", "success_prob",
                "rationale", "id")})
            self._pending = {"decision": decision, "verdict": entry["verdict"]}
        # control state: last STOP/PAUSE without a later RESUME persists
        if last_control == "STOP":
            self._stop = True
            self.state = SysState.STOPPED
        elif last_control == "PAUSE":
            self._paused = True
            self.state = SysState.PAUSED
        elif self._pending is not None:
            self.state = SysState.WAITING_HUMAN
        else:
            self.state = SysState.IDLE
        # re-register imported MCP tools (lazy reconnection on first call)
        self.capabilities.restore_registry()

    # ------------------------------------------------------------ commands
    def ingest_external(self, text: str, source: str) -> str:
        content_id = f"content_{len(self.taint.contents) + 1}"
        self.runtime.emit(Ev.CONTENT_INGESTED,
                          {"content_id": content_id, "text": text,
                           "trust": "external", "source": source},
                          Actor.ENVIRONMENT)
        return content_id

    def propose_goal(self, kind: NodeKind, label: str, priority: float,
                     actor: Actor = Actor.SYSTEM) -> str:
        gid = self.runtime.next_id("goal")
        n = node(gid, kind, label, status=NodeStatus.PROPOSED, priority=priority)
        self.runtime.emit(Ev.GOAL_PROPOSED, {"node": n}, actor)
        return gid

    def ratify_goal(self, node_id: str, actor: Actor) -> None:
        """Ratification rule: the system proposes, the human ratifies."""
        if actor != Actor.HUMAN:
            raise PermissionError(
                "meta-goals and persistent goals require explicit human ratification")
        self.runtime.emit(Ev.GOAL_RATIFIED, {"node_id": node_id}, actor)

    def human_edit_node(self, node_id: str, props: dict, actor: Actor,
                        status: str | None = None) -> None:
        if actor != Actor.HUMAN:
            raise PermissionError("manual edits carry the human identity")
        payload = {"node_id": node_id, "props": props}
        if status:
            payload["status"] = status
        self.runtime.emit(Ev.HUMAN_EDIT, payload, actor)

    def set_budget(self, name: str, limit: float, actor: Actor) -> None:
        set_budget(self.runtime, name, limit, actor)

    def update_config(self, changes: dict, actor: Actor) -> dict:
        """Runtime configuration is human-editable only; every change is
        an event (auditable, reapplied on recovery). The Config object is
        shared by reference with all projections, so a change takes
        effect everywhere immediately."""
        if actor != Actor.HUMAN:
            raise PermissionError("runtime configuration is human-editable only")
        applied = {}
        for key, value in changes.items():
            if key.startswith("_") or not hasattr(self.config, key):
                raise KeyError(f"unknown config field '{key}'")
            current = getattr(self.config, key)
            try:
                if isinstance(current, bool):
                    value = bool(value)
                elif isinstance(current, int):
                    value = int(value)
                elif isinstance(current, float):
                    value = float(value)
                elif isinstance(current, dict) and not isinstance(value, dict):
                    raise TypeError("must be an object")
            except (TypeError, ValueError) as exc:
                raise ValueError(f"config field '{key}': {exc}") from exc
            applied[key] = value
        self.runtime.emit(Ev.CONFIG_UPDATED, {"changes": applied}, actor)
        for k, v in applied.items():
            setattr(self.config, k, v)
        return applied

    # -------------------------------------------------------- capabilities
    def import_skill(self, path: str, actor: Actor) -> dict:
        """Import a skill package (M28); risky skills imported by the
        system stay disabled until the human approves."""
        skill = load_skill_package(path)
        return self.capabilities.import_skill(skill, actor)

    def set_skill_enabled(self, name: str, enabled: bool, actor: Actor) -> None:
        self.capabilities.set_skill_enabled(name, enabled, actor)

    def import_mcp_server(self, server_id: str, command: list[str],
                          actor: Actor) -> dict:
        return self.capabilities.import_mcp_server(server_id, command, actor)

    def approve_mcp_server(self, server_id: str, actor: Actor) -> None:
        self.capabilities.approve_mcp_server(server_id, actor)

    def set_tool_enabled(self, name: str, enabled: bool, actor: Actor) -> None:
        self.capabilities.set_tool_enabled(name, enabled, actor)

    def verify_capabilities(self) -> list[dict]:
        return self.capabilities.verify_all()

    # ---------------------------------------------------- human decisions
    def pending_decision(self) -> dict | None:
        return self._pending

    def resolve_pending(self, approve: bool, note: str = "") -> CycleResult | None:
        """Human decision on a HUMAN_REQUIRED verdict (decision inbox)."""
        if self._pending is None:
            return None
        decision: ProposedDecision = self._pending["decision"]
        verdict = self._pending["verdict"]
        self.supervisor.override(verdict["id"], Actor.HUMAN, approve, note)
        self._pending = None
        if not approve:
            self._denied_signatures.add(self._signature(decision))
            self.runtime.emit(Ev.HYPOTHESIS_PRUNED,
                              {"decision_id": decision.id, "reason": "human denial"},
                              Actor.HUMAN)
            self._set_state(SysState.IDLE)
            return CycleResult(self.cycle, "denied", decision.id)
        self._check_control()
        result = self._execute(decision)
        self._set_state(SysState.IDLE)
        return result

    def override_verdict(self, verdict_id: str, approve: bool, note: str = "") -> dict:
        """Override any recent verdict in either direction. Approving a
        denied, not-yet-executed decision re-executes it; revoking an
        executed one is recorded for audit (compensation is a later phase)."""
        entry = next((e for e in self.inbox.recent
                      if e["verdict"]["id"] == verdict_id), None)
        if entry is None:
            raise KeyError(verdict_id)
        if (self._pending is not None
                and self._pending["verdict"]["id"] == verdict_id):
            res = self.resolve_pending(approve, note)
            return {"resolved_pending": True, "result": res.status if res else None}
        self.supervisor.override(verdict_id, Actor.HUMAN, approve, note)
        rec = self.journal.records.get(entry["verdict"]["decision_id"], {})
        executed = bool(rec.get("execution"))
        if approve and entry["verdict"]["status"] == VerdictStatus.DENIED.value and not executed:
            d = entry["decision"]
            decision = ProposedDecision(**{k: d[k] for k in (
                "kind", "action_name", "params", "cost", "risk_class", "goal_refs",
                "derived_from", "tainted", "expected", "success_prob", "rationale", "id")})
            self._check_control()
            self._execute(decision)
            return {"re_executed": True}
        if not approve and executed:
            comp = self._compensate(rec)
            return {"recorded": True, "already_executed": True,
                    "compensated": comp}
        return {"recorded": True, "already_executed": executed}

    def _compensate(self, record: dict) -> bool:
        """A human revocation of an executed action triggers compensation
        when a compensating tool exists (spec: rollback/refund workflow).
        The revocation itself is the authorization."""
        d = record.get("decision", {})
        comp_tool = f"compensate.{d.get('action_name')}"
        if comp_tool not in self.registry.names(enabled_only=False):
            return False
        params = {"factor_id": d.get("params", {}).get("factor_id"),
                  "quantity": d.get("params", {}).get("quantity", 0),
                  "decision_id": d.get("id")}
        result = self.registry.execute(comp_tool, params)
        if result.status != "ok":
            self.runtime.emit(Ev.ERROR_DETECTED,
                              {"decision_id": d.get("id"),
                               "class": "compensation_failed",
                               "error": result.error}, Actor.SYSTEM)
            return False
        refunded = float(result.observation.get("refunded", 0.0))
        if refunded:
            self.runtime.emit(Ev.RESOURCE_SPENT,
                              {"name": "money", "amount": -refunded,
                               "decision_id": d.get("id"),
                               "compensation": True}, Actor.SYSTEM)
        fid = params["factor_id"]
        f = self.graph.node(fid) if fid else None
        if f is not None:
            newq = max(0, f["props"].get("acquired_qty", 0)
                       - int(params["quantity"] or 0))
            self.runtime.emit(Ev.NODE_UPDATED,
                              {"node_id": fid, "props": {"acquired_qty": newq}},
                              Actor.SYSTEM)
        self.runtime.emit(Ev.COMPENSATION_EXECUTED,
                          {"decision_id": d.get("id"), "tool": comp_tool,
                           "result": result.observation}, Actor.HUMAN)
        return True

    # --------------------------------------------------------- deliberation
    def open_deliberation(self, subject_kind: str, subject_id: str,
                          question: str, actor: Actor = Actor.HUMAN) -> dict:
        return self.deliberation.open(subject_kind, subject_id, question, actor)

    def reply_deliberation(self, thread_id: str, text: str,
                           actor: Actor = Actor.HUMAN) -> dict:
        return self.deliberation.reply(thread_id, text, actor)

    def resolve_deliberation(self, thread_id: str, outcome: str,
                             note: str = "", changes: dict | None = None,
                             actor: Actor = Actor.HUMAN) -> dict:
        """Close a thread with a binding outcome. 'confirmed' records
        agreement; 'modified' applies the agreed node edits with human
        provenance; 'cancelled' denies a pending decision, revokes an
        executed one (compensation path), or defers an active strategy
        (replan next cycle). Contested decision classes leave a dissent
        mark on their context signature for future advisories."""
        if actor != Actor.HUMAN:
            raise PermissionError("deliberation outcomes are decided by the human")
        th = self.deliberations.threads.get(thread_id)
        if th is None:
            raise KeyError(thread_id)
        if th["status"] != "OPEN":
            raise ValueError(f"thread {thread_id} is already resolved")
        if outcome not in ("confirmed", "modified", "cancelled"):
            raise ValueError(f"unknown outcome '{outcome}'")
        subject = th["subject"]
        effects: list[dict] = []
        if outcome == "modified" and changes:
            if isinstance(changes, list):          # typed change-set (M32)
                effects += self._apply_ops(changes, actor)
            elif isinstance(changes, dict):
                if isinstance(changes.get("ops"), list):
                    effects += self._apply_ops(changes["ops"], actor)
                node_id = changes.get("node_id")
                props = changes.get("props") or {}
                if node_id and props:
                    self.human_edit_node(node_id, props, actor)
                    effects.append({"type": "node_edited", "node_id": node_id,
                                    "props": props})
        # integration threads (M31): confirming/modifying weaves the
        # exogenous node per the (possibly edited) proposal
        packet = (th["messages"][0].get("packet") or {}) if th["messages"] else {}
        if (packet.get("checkpoint") == "integration"
                and outcome in ("confirmed", "modified")):
            proposal = packet.get("proposal") or {}
            if isinstance(changes, dict) and isinstance(changes.get("proposal"),
                                                        dict):
                proposal = changes["proposal"]
            applied = self.exogenous.apply_integration(
                packet["node_id"], proposal, actor)
            effects.append({"type": "integration_applied", **applied})
        if outcome == "cancelled" and subject["kind"] == "decision":
            rec = self.journal.records.get(subject["id"])
            if (self._pending is not None
                    and self._pending["decision"].id == subject["id"]):
                self.resolve_pending(False, note or "cancelled in deliberation")
                effects.append({"type": "pending_denied"})
            elif rec and rec.get("execution") and rec.get("verdict"):
                out = self.override_verdict(rec["verdict"]["id"], approve=False,
                                            note=note or "cancelled in deliberation")
                effects.append({"type": "revoked",
                                "compensated": bool(out.get("compensated"))})
        if outcome == "cancelled" and subject["kind"] == "strategy":
            b = self.strategies.branches.get(subject["id"])
            if b is not None and b["status"] == "ACTIVE":
                self.runtime.emit(Ev.STRATEGY_CHANGED,
                                  {"branch_id": b["id"],
                                   "reason": "human cancelled the branch in "
                                             "deliberation; replan next cycle"},
                                  Actor.HUMAN)
                effects.append({"type": "strategy_deferred",
                                "branch_id": b["id"]})
        resolution = {"outcome": outcome, "note": note, "effects": effects}
        if subject["kind"] == "decision" and outcome in ("cancelled", "modified"):
            sig = self._decision_signature(subject["id"])
            if sig is not None:
                resolution["signature"] = sig
        return self.deliberation.record_resolution(thread_id, resolution, actor)

    def _decision_signature(self, decision_id: str) -> str | None:
        """Context signature of a journaled decision - from its audit when
        available, else recomputed with the audit's feature formulas."""
        rec = self.journal.records.get(decision_id)
        if rec is None:
            return None
        feats = (rec.get("audit") or {}).get("features")
        if feats is None:
            d = rec["decision"]
            fsnap = {}
            fid = d["params"].get("factor_id")
            if fid and self.graph.node(fid):
                p = self.graph.node(fid)["props"]
                fsnap = {"importance": p.get("importance"),
                         "substitutability": p.get("substitutability")}
            feats = self._features_preview(d["action_name"], d["params"], fsnap)
        return PolicyProjection.signature(feats)

    # ------------------------------------------------------------ the loop
    def run(self, max_cycles: int | None = None) -> list[CycleResult]:
        results = []
        n = min(max_cycles or self.config.max_cycles_per_run,
                self.config.max_cycles_per_run)
        for _ in range(n):
            r = self.step()
            results.append(r)
            if r.status in ("waiting_human", "idle", "stopped", "paused", "escalated"):
                break
        return results

    def step(self) -> CycleResult:
        if self._stop:
            return CycleResult(self.cycle, "stopped")
        if self._paused:
            return CycleResult(self.cycle, "paused")
        if self._pending is not None:
            self._set_state(SysState.WAITING_HUMAN)
            return CycleResult(self.cycle, "waiting_human",
                               self._pending["decision"].id)

        self.cycle += 1
        self.runtime.cycle = self.cycle
        self.runtime.emit(Ev.CYCLE_STARTED, {"cycle": self.cycle}, Actor.SYSTEM)
        self._set_state(SysState.RUNNING)
        try:
            return self._cycle_body()
        except _Stopped:
            self.runtime.emit(Ev.CYCLE_COMPLETED,
                              {"cycle": self.cycle, "aborted": "stopped"}, Actor.SYSTEM)
            self._set_state(SysState.STOPPED)
            return CycleResult(self.cycle, "stopped")

    # ------------------------------------------------------- cycle phases
    def _cycle_body(self) -> CycleResult:
        self._check_control()
        self._reconcile()
        self._check_control()

        context = self._build_context()
        open_targets = self.graph.open_targets()
        if not context["factors"] or not open_targets:
            self.runtime.emit(Ev.CYCLE_COMPLETED,
                              {"cycle": self.cycle, "idle": True}, Actor.SYSTEM)
            self._set_state(SysState.IDLE)
            return CycleResult(self.cycle, "idle")

        # strategy branching: plan when nothing is active, then resolve the
        # branch's next actionable step for this cycle. Planning pauses
        # while a strategy-review disagreement awaits the human (M29).
        if not self._strategy_review_hold():
            self.strategy_engine.ensure(context)
            self._review_strategy()
        allowed = {f["id"] for f in context["factors"]}
        self._cycle_step_ref = self.strategy_engine.current_step_ref(allowed)

        # generative cognition: hypotheses, then independent critique
        response = self.gateway.ask("hypotheses", context)
        hyps = [h for h in response.hypotheses
                if self._signature(h) not in self._denied_signatures]
        for h in hyps:
            self.runtime.emit(Ev.HYPOTHESIS_CREATED,
                              {"hypothesis": h.to_dict()}, Actor.SYSTEM)
        for h in hyps:
            # provenance: proposals drawing on external content record their
            # claims explicitly (contradiction management catches them later)
            if h.derived_from and h.params.get("factor_id") and "unit_cost" in h.params:
                self.evidence.record_claim(h.params["factor_id"], "unit_cost",
                                           h.params["unit_cost"],
                                           h.derived_from[0], "external")
            # calibrated priors: claimed probabilities shrink toward the
            # observed rate (the LLM proposes; history calibrates)
            h.params.setdefault("claimed_success_prob", h.success_prob)
            h.success_prob = self.self_model.calibrated_success(
                h.params.get("domain", "general"), h.action_name, h.success_prob)
        if not hyps:
            return self._escalate("no viable hypotheses for open targets")

        antagonisms = []
        for fid in sorted({h.params.get("factor_id") for h in hyps if h.params.get("factor_id")}):
            antagonisms.extend(self.graph.antagonisms(fid))
        critique = self.gateway.ask(
            "critique", {"hypotheses": [h.to_dict() for h in hyps],
                         "antagonisms": antagonisms})
        conflicts = critique.risks
        for c in conflicts:
            key = ("conflict", c.get("factor"))
            if key not in self._conflicts_emitted:
                self._conflicts_emitted.add(key)
                self.runtime.emit(Ev.CONFLICT_DETECTED, c, Actor.SYSTEM)
                # a conflict touching a human directive earns a
                # consultation thread (M32): the AI asks before trading
                # off what the human explicitly decided
                touched = [g for g in (list(c.get("supports", []))
                                       + list(c.get("harms", [])))
                           if (self.graph.node(g) or {}).get("kind")
                           == NodeKind.DIRECTIVE.value]
                if touched:
                    self.deliberation.open_system(
                        f"conflict involves your directive(s) "
                        f"{', '.join(sorted(set(touched)))}: factor "
                        f"'{c.get('factor')}' supports "
                        f"{c.get('supports')} but harms {c.get('harms')}. "
                        f"How should I weigh this?",
                        {"checkpoint": "consultation", "conflict": c,
                         "cycle": self.cycle})

        self._check_control()

        # arbitration with the sensitivity gate
        ranked, unstable = score_candidates(self.graph, self.budgets, hyps,
                                            self.config)
        # adherence bonus: the active strategy's next step gets a small edge,
        # deliberately too small to overrule a genuinely better alternative
        if self._cycle_step_ref is not None:
            _, step = self._cycle_step_ref
            for s in ranked:
                if (s.hyp.action_name == step.get("action_name")
                        and s.hyp.params.get("factor_id") == step.get("factor_id")):
                    s.utility += self.config.strategy_adherence_bonus
                    s.parts["strategy_bonus"] = self.config.strategy_adherence_bonus
            ranked = sorted(ranked, key=lambda s: (-s.utility, s.hyp.action_name,
                                                   str(sorted(s.hyp.params.items()))))
        selected = ranked[0]
        if unstable:
            research = next((s for s in ranked
                             if s.hyp.action_name == "research_price"), None)
            self.runtime.emit(Ev.SENSITIVITY_UNSTABLE,
                              {"best": selected.hyp.action_name,
                               "resolution": "information_gain" if research else "escalate"},
                              Actor.SYSTEM)
            if research is not None:
                selected = research
            else:
                return self._escalate("decision unstable under uncertainty; "
                                      "no information-gain action available")

        decision = self._to_decision(selected.hyp)
        fsnap = {}
        fid = selected.hyp.params.get("factor_id")
        if fid and self.graph.node(fid):
            p = self.graph.node(fid)["props"]
            fsnap = {"importance": p.get("importance"),
                     "substitutability": p.get("substitutability")}
        strategy_info = None
        if self._cycle_step_ref is not None:
            bid, step = self._cycle_step_ref
            if (decision.action_name == step.get("action_name")
                    and decision.params.get("factor_id") == step.get("factor_id")):
                strategy_info = {"branch_id": bid, "step": step}
        dec_context = {"budget_limit": self.budgets.limit("money"),
                       "budget_remaining": self.budgets.remaining("money"),
                       "factor_snapshot": fsnap, "unstable": unstable,
                       "strategy": strategy_info}
        self.runtime.emit(Ev.DECISION_MADE, {
            "decision": decision.to_dict(),
            "alternatives": [{"action_name": s.hyp.action_name,
                              "params": s.hyp.params,
                              "utility": round(s.utility, 4),
                              "parts": s.parts} for s in ranked],
            "context": dec_context,
            "conflicts": conflicts,
        }, Actor.SYSTEM)
        self.policy_engine.shadow_evaluate(decision.to_dict(), dec_context)

        # cross-AI review (M29): a second AI reviews the decision before
        # it is enacted; the matrix decides rounds and the disagreement
        # override (discuss with the human vs primary decides)
        advisories = []
        escalate = None
        review = self.reviewer.review(
            "decision", decision.to_dict(),
            {"factor_snapshot": fsnap,
             "budget_remaining": self.budgets.remaining("money")})
        if review.get("outcome") == "withdrawn":
            self._denied_signatures.add(self._signature(decision))
            self.runtime.emit(Ev.HYPOTHESIS_PRUNED,
                              {"decision_id": decision.id,
                               "reason": "cross-AI review: the primary "
                                         "conceded; withdrawn"},
                              Actor.SYSTEM)
            self.runtime.emit(Ev.CYCLE_COMPLETED,
                              {"cycle": self.cycle, "denied": decision.id},
                              Actor.SYSTEM)
            return CycleResult(self.cycle, "denied", decision.id)
        if review.get("outcome") == "disagreement_human":
            objs = "; ".join(o.get("reason", "") for o in
                             review.get("standing_objections", []))
            escalate = [f"no cross-AI consensus after {review['rounds']} "
                        f"round(s): {objs or 'unspecified objections'}"]
        elif review.get("outcome") == "disagreement_primary":
            advisories.append("cross-AI reviewer dissent recorded; the "
                              "primary decided per the review matrix")

        # behavioral recurrence: past failures with the same context
        # signature become an advisory on the verdict (spec: Auditor Agent
        # and Behavioral Recurrence)
        preview = self._features_preview(decision.action_name, decision.params,
                                         fsnap)
        sig = PolicyProjection.signature(preview)
        for adv in (self.self_model.recurrence_advisory(sig),
                    self.self_model.dissent_advisory(sig)):
            if adv:
                advisories.append(adv)

        # deterministic authority: the supervisor rules before anything runs
        verdict = self.supervisor.evaluate(decision, self.cycle,
                                           advisories=advisories,
                                           escalate=escalate)
        if verdict["status"] == VerdictStatus.DENIED.value:
            self._denied_signatures.add(self._signature(decision))
            self.runtime.emit(Ev.HYPOTHESIS_PRUNED,
                              {"decision_id": decision.id,
                               "reason": "supervisor denial"}, Actor.SYSTEM)
            self.runtime.emit(Ev.CYCLE_COMPLETED,
                              {"cycle": self.cycle, "denied": decision.id}, Actor.SYSTEM)
            return CycleResult(self.cycle, "denied", decision.id)
        if verdict["status"] == VerdictStatus.HUMAN_REQUIRED.value:
            self._pending = {"decision": decision, "verdict": verdict}
            self.runtime.emit(Ev.CYCLE_COMPLETED,
                              {"cycle": self.cycle, "waiting": decision.id}, Actor.SYSTEM)
            self._set_state(SysState.WAITING_HUMAN)
            return CycleResult(self.cycle, "waiting_human", decision.id)

        self._check_control()
        result = self._execute(decision)
        self.runtime.emit(Ev.CYCLE_COMPLETED,
                          {"cycle": self.cycle, "executed": decision.id}, Actor.SYSTEM)
        return result

    # ------------------------------------------------- cross-AI review
    def _strategy_review_hold(self) -> bool:
        """Replanning pauses while a strategy-review disagreement awaits
        the human in an open system thread (recovery-safe: derived from
        the deliberation projection, not volatile state)."""
        return any(t["opened_by"] == "system"
                   and (t["messages"][0].get("packet") or {})
                   .get("checkpoint") == "strategy"
                   for t in self.deliberations.open_threads())

    def _review_strategy(self) -> None:
        if not self.reviewer.policy("strategy").get("enabled"):
            return
        b = self.strategies.active()
        if b is None or self.reviews.for_subject(b["id"]):
            return
        r = self.reviewer.review(
            "strategy", b,
            {"budget_remaining": self.budgets.remaining("money")})
        if r.get("outcome") in ("withdrawn", "disagreement_human"):
            self.runtime.emit(Ev.STRATEGY_CHANGED,
                              {"branch_id": b["id"],
                               "reason": f"cross-AI review: {r['outcome']}"},
                              Actor.SYSTEM)
            if r["outcome"] == "disagreement_human":
                objs = "; ".join(o.get("reason", "") for o in
                                 r.get("standing_objections", []))
                self.deliberation.open_system(
                    f"cross-AI review disagreement on strategy {b['id']} "
                    f"('{b['label']}'): {objs or 'unspecified objections'}. "
                    f"Replanning is paused until you resolve this thread.",
                    {"checkpoint": "strategy", "branch_id": b["id"],
                     "review_id": r["id"], "cycle": self.cycle})

    def add_knowledge(self, text: str, meta: dict | None = None,
                      actor: Actor = Actor.HUMAN) -> str:
        return _add_knowledge(self.runtime, text, meta, actor)

    # ------------------------------------------------- exogenous (M31)
    def _integration_thread(self, node_id: str) -> dict | None:
        for t in self.deliberations.open_threads():
            p = (t["messages"][0].get("packet") or {}) if t["messages"] else {}
            if (t["opened_by"] == "system"
                    and p.get("checkpoint") == "integration"
                    and p.get("node_id") == node_id):
                return t
        return None

    def accept_opportunity(self, node_id: str,
                           actor: Actor = Actor.HUMAN) -> dict:
        """Accepting an opportunity fact = confirming its integration
        thread (weaves it and activates the node)."""
        th = self._integration_thread(node_id)
        if th is not None:
            return self.resolve_deliberation(th["id"], "confirmed",
                                             "opportunity accepted",
                                             actor=actor)
        # no open thread (e.g. resolved earlier without applying): weave
        # from the last recorded proposal
        proposal = next((e.payload["proposal"] for e in
                         reversed(self.runtime.events())
                         if e.type == Ev.INTEGRATION_PROPOSED.value
                         and e.payload.get("node_id") == node_id), None)
        if proposal is None:
            raise KeyError(node_id)
        return self.exogenous.apply_integration(node_id, proposal, actor)

    def decline_opportunity(self, node_id: str,
                            actor: Actor = Actor.HUMAN) -> dict:
        if actor != Actor.HUMAN:
            raise PermissionError("opportunities are declined by the human")
        n = self.graph.node(node_id)
        if n is None or n["kind"] not in {k.value for k in EXOGENOUS_KINDS}:
            raise KeyError(node_id)
        th = self._integration_thread(node_id)
        if th is not None:
            self.deliberation.record_resolution(
                th["id"], {"outcome": "cancelled",
                           "note": "opportunity declined", "effects": []},
                actor)
        self.runtime.emit(Ev.NODE_INVALIDATED,
                          {"node_id": node_id,
                           "status": NodeStatus.INVALIDATED.value,
                           "reason": "opportunity declined"}, actor)
        return {"declined": node_id}

    def _apply_ops(self, ops: list, actor: Actor) -> list[dict]:
        """Typed change-set operations (M32): any deliberation thread can,
        on the human's request, modify the overall scenario and targets -
        each op routed through its existing human-identity channel."""
        effects: list[dict] = []
        for op in ops:
            k = op.get("op")
            if k == "node_props":
                self.human_edit_node(op["node_id"], op.get("props", {}), actor)
                effects.append({"type": "node_edited",
                                "node_id": op["node_id"]})
            elif k == "new_directive":
                d = self.exogenous.issue_directive(
                    op["label"], op.get("description", ""),
                    float(op.get("weight", 0.6)), op.get("horizon", "short"),
                    op.get("directive_type", "context"), actor)
                effects.append({"type": "directive_issued", "id": d["id"]})
            elif k == "new_fact":
                f = self.exogenous.record_fact(
                    op["label"], op.get("description", ""),
                    float(op.get("weight", 0.5)), op.get("mode", "imposed"),
                    actor)
                effects.append({"type": "fact_recorded", "id": f["id"]})
            elif k == "propose_goal":
                kind = NodeKind(op.get("kind", "OBJECTIVE"))
                gid = self.propose_goal(kind, op["label"],
                                        float(op.get("priority", 0.5)), actor)
                if op.get("ratify") and kind in RATIFICATION_KINDS:
                    self.ratify_goal(gid, actor)
                effects.append({"type": "goal_proposed", "id": gid})
            elif k == "defer_target":
                self.runtime.emit(Ev.TARGET_DEFERRED,
                                  {"node_id": op["node_id"],
                                   "reason": op.get("reason",
                                                    "human change-set")},
                                  actor)
                effects.append({"type": "target_deferred",
                                "node_id": op["node_id"]})
            elif k == "set_budget":
                self.set_budget(op["name"], float(op["limit"]), actor)
                effects.append({"type": "budget_set", "name": op["name"],
                                "limit": float(op["limit"])})
            elif k == "create_guardrail":
                g = guardrail(
                    description=op["description"],
                    tier=int(op.get("tier", 2)),
                    rule=op.get("rule", {}),
                    flexibility=Flexibility(op.get("flexibility",
                                                   "SOFT_BLOCK")),
                    conditions=op.get("conditions"))
                self.guardrails.create(g, actor)
                effects.append({"type": "guardrail_created", "id": g["id"]})
            else:
                raise ValueError(f"unknown change-set op '{k}'")
        return effects

    # -------------------------------------------------------- helpers
    def _escalate(self, reason: str) -> CycleResult:
        """Escalations are bidirectional deliberation: the packet becomes
        a system-opened discussion thread the human can answer in place."""
        self.runtime.emit(Ev.HUMAN_ESCALATION, {"reason": reason}, Actor.SYSTEM)
        self.deliberation.open_system(reason, {
            "reason": reason, "cycle": self.cycle,
            "budget_remaining": self.budgets.remaining("money"),
            "open_targets": [t["id"] for t in self.graph.open_targets()]})
        self.runtime.emit(Ev.CYCLE_COMPLETED,
                          {"cycle": self.cycle, "escalated": True}, Actor.SYSTEM)
        self._set_state(SysState.ESCALATED)
        return CycleResult(self.cycle, "escalated")

    def _features_preview(self, action_name: str, params: dict,
                          fsnap: dict) -> dict:
        """Same feature formulas the audit uses, computed at decision time
        for behavioral-recurrence lookup."""
        limit = self.budgets.limit("money") or 1.0
        remaining = self.budgets.remaining("money")
        cost = float(params.get("total_cost", 0.0))
        imp = fsnap.get("importance")
        sub = fsnap.get("substitutability")
        return {
            "action": action_name,
            "domain": params.get("domain", "general"),
            "budget_constrained": (remaining - cost) < 0.5 * limit,
            "picked_high_importance_low_subst": (
                float(imp or 0.0) >= 0.7
                and float(sub if sub is not None else 1.0) <= 0.4),
        }

    @staticmethod
    def _signature(h) -> tuple:
        params = h.params if isinstance(h, (Hypothesis, ProposedDecision)) else h["params"]
        name = h.action_name if not isinstance(h, dict) else h["action_name"]
        derived = tuple(h.derived_from if not isinstance(h, dict) else h.get("derived_from", []))
        return (name, params.get("factor_id"), derived)

    def _to_decision(self, h: Hypothesis) -> ProposedDecision:
        kind = (DecisionKind.TOOL_INVOCATION.value
                if h.action_name in self.registry.names()
                else DecisionKind.STRATEGY_SELECTION.value)
        goal_refs = []
        fid = h.params.get("factor_id")
        if fid:
            goal_refs = sorted(self.graph.goal_effects(fid).keys())
        return ProposedDecision(
            kind=kind, action_name=h.action_name, params=h.params,
            cost=float(h.params.get("total_cost", 0.0)),
            risk_class=h.risk_class, goal_refs=goal_refs,
            derived_from=h.derived_from, expected=h.expected,
            success_prob=h.success_prob, rationale=h.rationale,
            id=self.runtime.next_id("dec"))

    def _build_context(self) -> dict:
        factor_ids: set[str] = set()
        for t in self.graph.open_targets():
            for e in self.graph.in_edges(t["id"], {RelType.REQUIRED}):
                factor_ids.add(e["src"])
                factor_ids.update(self.graph.substitutes_of(e["src"]))
        factors = []
        for fid in sorted(factor_ids):
            n = self.graph.node(fid)
            if n is None or n["status"] != NodeStatus.ACTIVE.value:
                continue
            p = n["props"]
            factors.append({"id": fid, "label": n["label"],
                            "importance": p.get("importance", 0.5),
                            "substitutability": p.get("substitutability", 0.5),
                            "unit_cost": p.get("unit_cost"),
                            "cost_confidence": p.get("cost_confidence", 0.3),
                            "quantity_needed": p.get("quantity_needed", 1),
                            "acquired_qty": p.get("acquired_qty", 0)})
        goals = [{"id": g["id"], "label": g["label"],
                  "priority": g["props"].get("priority", 0.5)}
                 for g in sorted(self.graph.active_goals(), key=lambda x: x["id"])]
        directives = [{"id": d["id"], "label": d["label"],
                       "weight": d["props"].get("priority", 0.5),
                       "type": d["props"].get("directive_type"),
                       "horizon": d["props"].get("horizon")}
                      for d in sorted(self.graph.by_kind(
                          NodeKind.DIRECTIVE, status=NodeStatus.ACTIVE),
                          key=lambda x: x["id"])]
        facts = [{"id": f["id"], "label": f["label"],
                  "weight": f["props"].get("importance", 0.5),
                  "mode": f["props"].get("mode")}
                 for f in sorted(self.graph.by_kind(
                     NodeKind.FACT, status=NodeStatus.ACTIVE),
                     key=lambda x: x["id"])]
        tools = self.registry.names()
        # progressive disclosure: only skills triggered by the current
        # context enter the briefing; their text stays labeled untrusted
        context_text = " ".join(
            [g["label"] for g in goals] + [f["id"] for f in factors]
            + [f["label"] for f in factors] + tools + ["purchase budget"])
        skills = [{"name": s["name"], "description": s["description"],
                   "instructions": s["instructions"], "trust": s["trust"]}
                  for s in self.capability_store.enabled_skills()
                  if matches_context(s, context_text)]
        return {
            "goals": goals,
            "directives": directives,
            "facts": facts,
            "factors": factors,
            "budget": {"money": {"limit": self.budgets.limit("money"),
                                 "remaining": self.budgets.remaining("money")}},
            # attention hygiene (M17): old external content leaves the
            # working briefing; the event log keeps it for audit/replay
            "external_content": [
                {"id": c["id"], "trust": c["trust"],
                 "text": next((e.payload["text"] for e in self.runtime.events()
                               if e.type == Ev.CONTENT_INGESTED.value
                               and e.payload["content_id"] == c["id"]), "")}
                for c in self.taint.contents
                if c.get("cycle") is None
                or (self.cycle - c["cycle"])
                <= self.config.external_content_context_cycles],
            "policies": [p["description"] for p in
                         self.policies.matching({"ACTIVE"})],
            "skills": skills,
            # name alone is enough for the scripted mock, but a real model
            # cannot guess the params contract: ship description (which
            # carries it) and risk class with every enabled tool
            "tools": [{"name": s.name, "description": s.description,
                       "risk_class": s.risk_class,
                       "description_trust": s.description_trust}
                      for s in self.registry.specs() if s.enabled],
        }

    def _reconcile(self) -> None:
        """Event-driven reconciliation over the dirty subgraph + due reviews."""
        dirty = set(self.graph.dirty)
        self.graph.dirty.clear()
        for t in self.graph.open_targets():
            required = self.graph.in_edges(t["id"], {RelType.REQUIRED})
            if not required:
                continue
            satisfied, substituted = [], []
            for e in required:
                f = self.graph.node(e["src"])
                if f is None:
                    continue
                p = f["props"]
                if p.get("acquired_qty", 0) >= p.get("quantity_needed", 1):
                    satisfied.append(f["id"])
                    continue
                for sid in self.graph.substitutes_of(f["id"]):
                    s = self.graph.node(sid)
                    if s and s["props"].get("acquired_qty", 0) >= s["props"].get("quantity_needed", 1):
                        substituted.append((f["id"], sid, e["id"]))
                        break
            done = {x for x in satisfied} | {f for f, _, _ in substituted}
            if done >= {e["src"] for e in required}:
                for f, sid, eid in substituted:
                    self.runtime.emit(Ev.EDGE_UPDATED,
                                      {"edge_id": eid, "validity_status":
                                       NodeStatus.SUPERSEDED.value}, Actor.SYSTEM)
                    self.runtime.emit(Ev.NODE_INVALIDATED,
                                      {"node_id": f, "status": NodeStatus.SUPERSEDED.value,
                                       "reason": f"substituted by {sid}"}, Actor.SYSTEM)
                self.runtime.emit(Ev.TARGET_COMPLETED,
                                  {"node_id": t["id"],
                                   "substitutions": [{"factor": f, "by": s}
                                                     for f, s, _ in substituted]},
                                  Actor.SYSTEM)
        # dynamic reprioritization: a target whose every acquisition route
        # (factor and substitutes) has a KNOWN cost above the remaining
        # budget is DEFERRED - revisitable, not abandoned - freeing
        # resources and attention for higher-value pursuits.
        remaining = self.budgets.remaining("money")
        for t in self.graph.open_targets():
            required = self.graph.in_edges(t["id"], {RelType.REQUIRED})
            if not required:
                continue
            starved = None
            for e in required:
                f = self.graph.node(e["src"])
                if f is None:
                    continue
                fp = f["props"]
                if fp.get("acquired_qty", 0) >= fp.get("quantity_needed", 1):
                    continue
                options = [f] + [self.graph.node(s)
                                 for s in self.graph.substitutes_of(f["id"])]
                affordable = False
                for o in options:
                    if o is None or o["status"] != NodeStatus.ACTIVE.value:
                        continue
                    op = o["props"]
                    cost = op.get("unit_cost")
                    need = op.get("quantity_needed", 1) - op.get("acquired_qty", 0)
                    if cost is None or cost * max(need, 0) <= remaining:
                        affordable = True
                        break
                if not affordable:
                    starved = f["id"]
                    break
            if starved is not None:
                self.runtime.emit(Ev.TARGET_DEFERRED,
                                  {"node_id": t["id"], "factor": starved,
                                   "reason": "no affordable acquisition route "
                                             "within the remaining budget"},
                                  Actor.SYSTEM)
                self.runtime.emit(Ev.RESOURCE_REALLOCATED,
                                  {"resource": "money", "away_from": t["id"],
                                   "remaining": remaining,
                                   "reason": "budget reallocated toward "
                                             "higher-value active pursuits"},
                                  Actor.SYSTEM)

        # exogenous blocking (M31): a target with an active BLOCK/INHIBIT
        # edge from an ACTIVE directive/fact is deferred - reversibly: it
        # reactivates the moment the blocker is retired ("no meetings
        # while the vacation directive stands")
        exo = {k.value for k in EXOGENOUS_KINDS}
        for t in self.graph.open_targets():
            for e in self.graph.in_edges(t["id"], {RelType.BLOCK,
                                                   RelType.INHIBIT}):
                src = self.graph.node(e["src"])
                if (src is not None and src["kind"] in exo
                        and src["status"] == NodeStatus.ACTIVE.value):
                    self.runtime.emit(Ev.TARGET_DEFERRED,
                                      {"node_id": t["id"],
                                       "blocked_by": src["id"],
                                       "reason": f"blocked by "
                                                 f"{src['kind'].lower()} "
                                                 f"{src['id']} "
                                                 f"('{src['label']}')"},
                                      Actor.SYSTEM)
                    break
        for t in self.graph.by_kind(NodeKind.TARGET, NodeKind.SUB_TARGET,
                                    status=NodeStatus.DEFERRED):
            blocker_id = t["props"].get("deferred_by")
            if not blocker_id:
                continue   # budget deferrals are not blocker-bound
            blocker = self.graph.node(blocker_id)
            edge_alive = any(
                e["src"] == blocker_id
                for e in self.graph.in_edges(t["id"], {RelType.BLOCK,
                                                       RelType.INHIBIT}))
            if (blocker is None
                    or blocker["status"] != NodeStatus.ACTIVE.value
                    or not edge_alive):
                self.runtime.emit(Ev.NODE_UPDATED,
                                  {"node_id": t["id"],
                                   "status": NodeStatus.ACTIVE.value,
                                   "props": {"deferred_by": None},
                                   "reason": "blocker retired"},
                                  Actor.SYSTEM)

        # periodic human consultation (M32, config-gated): the system asks
        # for a sync on targets, limits and strategy
        n_cons = self.config.consultation_interval_cycles
        if (n_cons and self.cycle and self.cycle % n_cons == 0
                and not any((t["messages"][0].get("packet") or {})
                            .get("checkpoint") == "consultation"
                            for t in self.deliberations.open_threads()
                            if t["opened_by"] == "system")):
            summary = self.deliberation._evidence("scenario", "overall")
            self.deliberation.open_system(
                f"periodic sync (cycle {self.cycle}): "
                f"{len(summary['open_targets'])} open / "
                f"{len(summary['deferred_targets'])} deferred target(s), "
                f"budget remaining {summary['budget'].get('remaining')}. "
                f"Reply to discuss targets, limits or strategy; resolve to "
                f"acknowledge.",
                {"checkpoint": "consultation", "cycle": self.cycle,
                 "summary": summary})

        # macro-cycle maintenance: graph hygiene - stale, never-corroborated
        # HYPOTHESIZED edges are pruned (causal-propagation guardrails)
        if self.cycle and self.cycle % self.config.macro_interval_cycles == 0:
            pruned = []
            for e in list(self.graph.edges.values()):
                if (e["validation_status"] == "HYPOTHESIZED"
                        and e["validity_status"] == NodeStatus.ACTIVE.value
                        and (self.cycle - e.get("_cycle", 0))
                        > self.config.hypothesized_edge_ttl):
                    self.runtime.emit(Ev.EDGE_UPDATED,
                                      {"edge_id": e["id"],
                                       "validity_status":
                                       NodeStatus.INVALIDATED.value},
                                      Actor.SYSTEM)
                    pruned.append(e["id"])
            if pruned:
                self.runtime.emit(Ev.GRAPH_MAINTENANCE,
                                  {"cycle": self.cycle, "pruned_edges": pruned,
                                   "reason": "hypothesized edges never "
                                             "corroborated within the TTL"},
                                  Actor.SYSTEM)

        # periodic goal re-evaluation (review_interval per node)
        for g in self.graph.active_goals():
            last = g["props"].get("last_review_cycle", 0)
            if self.cycle - last >= g.get("review_interval", 3):
                self.runtime.emit(Ev.GOAL_REEVALUATED,
                                  {"node_id": g["id"], "still_valid": True,
                                   "cycle": self.cycle}, Actor.SYSTEM)
                self.runtime.emit(Ev.NODE_UPDATED,
                                  {"node_id": g["id"],
                                   "props": {"last_review_cycle": self.cycle}},
                                  Actor.SYSTEM)

    def _execute(self, decision: ProposedDecision) -> CycleResult:
        self._check_control()
        result = self.registry.execute(decision.action_name, decision.params)
        did = decision.id
        if result.status == "ok":
            obs = result.observation
            self.runtime.emit(Ev.ACTION_EXECUTED,
                              {"decision_id": did, "result": obs}, Actor.SYSTEM)
            if decision.action_name == "purchase":
                self.runtime.emit(Ev.RESOURCE_SPENT,
                                  {"name": "money",
                                   "amount": float(obs.get("total_cost", 0.0)),
                                   "decision_id": did}, Actor.SYSTEM)
                f = self.graph.node(obs["factor_id"])
                if f is not None:
                    newq = f["props"].get("acquired_qty", 0) + int(obs.get("quantity", 0))
                    self.runtime.emit(Ev.NODE_UPDATED,
                                      {"node_id": obs["factor_id"],
                                       "props": {"acquired_qty": newq}}, Actor.SYSTEM)
            elif decision.action_name == "research_price":
                self.runtime.emit(Ev.NODE_UPDATED,
                                  {"node_id": obs["factor_id"],
                                   "props": {"unit_cost": obs["unit_cost"],
                                             "cost_confidence": 0.95}}, Actor.SYSTEM)
                # contradiction management: an observation that conflicts
                # with a standing external claim becomes explicit evidence
                self.evidence.check_observation(obs["factor_id"], "unit_cost",
                                                obs["unit_cost"],
                                                "market:research_price")
            self.runtime.emit(Ev.OBSERVATION_RECEIVED,
                              {"decision_id": did, "observation": obs},
                              Actor.ENVIRONMENT)
            self.runtime.emit(Ev.OUTCOME_RECORDED,
                              {"decision_id": did, "success": True}, Actor.SYSTEM)
            matched, deviation = self._verify(decision, obs)
            self.runtime.emit(Ev.VERIFICATION_COMPLETED,
                              {"decision_id": did, "matched": matched,
                               "deviation": deviation}, Actor.SYSTEM)
            status = "executed"
        else:
            self.runtime.emit(Ev.ACTION_FAILED,
                              {"decision_id": did, "error": result.error},
                              Actor.SYSTEM)
            self.runtime.emit(Ev.OUTCOME_RECORDED,
                              {"decision_id": did, "success": False,
                               "error": result.error}, Actor.SYSTEM)
            status = "failed"

        self.strategy_engine.note_execution(self._cycle_step_ref, decision,
                                            status == "executed")
        audit_payload = self.audit_engine.run(self.journal.records[did])
        self.counterfactual.analyze(self.journal.records[did])
        # cross-AI review of the retrospective analysis (M29): a contested
        # audit is discussed with the human and never feeds policy
        # learning until then; in primary_decides mode learning proceeds
        # with the dissent on record
        r = self.reviewer.review(
            "retrospective",
            {"decision_id": did, "audit": audit_payload,
             "counterfactual": self.journal.records[did].get("counterfactual")},
            {})
        if r.get("outcome") == "disagreement_human":
            objs = "; ".join(o.get("reason", "") for o in
                             r.get("standing_objections", []))
            self.deliberation.open_system(
                f"cross-AI review contests the retrospective analysis of "
                f"{did}: {objs or 'unspecified objections'}",
                {"checkpoint": "retrospective", "decision_id": did,
                 "review_id": r["id"], "cycle": self.cycle})
        if r.get("outcome") not in ("disagreement_human", "withdrawn"):
            self.policy_engine.learn(audit_payload)
        self._apprentice_check(audit_payload["features"].get("domain", "general"))
        return CycleResult(self.cycle, status, did)

    def _verify(self, decision: ProposedDecision, obs: dict) -> tuple[bool, dict]:
        deviation = {}
        exp = decision.expected
        if "factor_acquired" in exp and exp["factor_acquired"] != obs.get("factor_id"):
            deviation["factor"] = {"expected": exp["factor_acquired"],
                                   "actual": obs.get("factor_id")}
        if "total_cost" in exp:
            actual = float(obs.get("total_cost", 0.0))
            if abs(actual - float(exp["total_cost"])) > 1e-6:
                deviation["total_cost"] = {"expected": exp["total_cost"],
                                           "actual": actual}
        if "cost_known" in exp and obs.get("unit_cost") is None:
            deviation["cost_known"] = {"expected": exp["cost_known"], "actual": None}
        return (not deviation), deviation

    def _apprentice_check(self, domain: str) -> None:
        """Poor calibration earns tighter supervision: the system itself
        proposes a restrictive Tier 2 guardrail (which self-activates)."""
        if not self.calibration.poorly_calibrated(domain):
            return
        for g in self.guardrails.active(tier=2):
            if (g["rule"].get("kind") == "apprentice_domain"
                    and g["rule"].get("domain") == domain):
                return
        self.guardrails.create(guardrail(
            description=f"apprentice mode: human review for '{domain}' "
                        f"(measured calibration is poor)",
            tier=2,
            rule={"kind": "apprentice_domain", "domain": domain,
                  "risk_class_at_least": "FINANCIAL"},
            flexibility=Flexibility.SOFT_BLOCK,
            direction="restrictive",
            provenance="system_calibration",
            id=self.runtime.next_id("gr2")), Actor.SYSTEM)
