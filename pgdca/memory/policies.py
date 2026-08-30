"""Policy lifecycle with learning guardrails.

Episodes become policies only with minimum independent evidence; a new
policy enters SHADOW mode (it recommends without acting, and agreement
with actual decisions is logged) before it may become ACTIVE. Seed
policies are hand-written, human-provenance, and may start ACTIVE.
(spec: Policy Representation + lifecycle guardrails)
"""
from __future__ import annotations

import json

from ..config import Config
from ..events import Actor, Ev, Event


class PolicyProjection:
    def __init__(self):
        self.policies: dict[str, dict] = {}
        # behavioral recurrence: features signature -> decision_ids with good decision quality
        self.pattern_episodes: dict[str, list[str]] = {}

    @staticmethod
    def signature(features: dict) -> str:
        keys = ("action", "budget_constrained", "picked_high_importance_low_subst")
        return json.dumps({k: features.get(k) for k in keys}, sort_keys=True)

    def apply(self, ev: Event) -> None:
        t, p = ev.type, ev.payload
        if t == Ev.POLICY_CREATED.value:
            pol = p["policy"]
            self.policies[pol["id"]] = pol
        elif t == Ev.POLICY_UPDATED.value:
            pol = self.policies.get(p["policy_id"])
            if pol is not None:
                pol.update(p.get("changes", {}))
        elif t == Ev.POLICY_SHADOW_EVALUATED.value:
            pol = self.policies.get(p["policy_id"])
            if pol is not None and p.get("agrees"):
                pol["agreements"] = pol.get("agreements", 0) + 1
        elif t == Ev.AUDIT_COMPLETED.value:
            feats = p.get("features", {})
            if (p.get("decision_quality", 0.0) >= 0.7
                    and feats.get("picked_high_importance_low_subst")):
                sig = self.signature(feats)
                eps = self.pattern_episodes.setdefault(sig, [])
                if p["decision_id"] not in eps:
                    eps.append(p["decision_id"])

    def by_signature(self, sig: str) -> dict | None:
        for pol in self.policies.values():
            if pol.get("features_signature") == sig:
                return pol
        return None

    def matching(self, statuses: set[str]) -> list[dict]:
        return sorted((p for p in self.policies.values() if p["status"] in statuses),
                      key=lambda p: p["id"])

    def snapshot(self) -> list[dict]:
        return sorted(self.policies.values(), key=lambda p: p["id"])


class PolicyEngine:
    """Turns recurring well-made decisions into policies (via the
    abstraction role of the LLM gateway) and manages SHADOW -> ACTIVE."""

    def __init__(self, runtime, projection: PolicyProjection, gateway,
                 config: Config | None = None):
        self.runtime = runtime
        self.projection = projection
        self.gateway = gateway
        self.config = config or Config()

    def learn(self, audit_payload: dict) -> dict | None:
        feats = audit_payload.get("features", {})
        sig = PolicyProjection.signature(feats)
        episodes = self.projection.pattern_episodes.get(sig, [])
        existing = self.projection.by_signature(sig)
        if existing is not None:
            if audit_payload["decision_id"] in episodes:
                self.runtime.emit(Ev.POLICY_UPDATED,
                                  {"policy_id": existing["id"],
                                   "changes": {"evidence_count": len(episodes)}},
                                  Actor.SYSTEM)
            return None
        if len(episodes) < self.config.policy_min_evidence:
            return None
        # abstraction is generative work: ask the gateway
        resp = self.gateway.ask("abstraction", {"features": feats})
        policy = {
            "id": self.runtime.next_id("pol"),
            "description": resp.summary,
            "status": "SHADOW",   # never straight to ACTIVE for learned policies
            "features_signature": sig,
            "applicable_context": {"domain": feats.get("domain", "general")},
            "evidence_count": len(episodes),
            "agreements": 0,
            "provenance": "learned",
        }
        self.runtime.emit(Ev.POLICY_CREATED, {"policy": policy}, Actor.SYSTEM)
        return policy

    def shadow_evaluate(self, decision: dict, context: dict) -> None:
        """Called at selection time: shadow policies recommend without acting."""
        fsnap = context.get("factor_snapshot", {})
        qualifies = (float(fsnap.get("importance", 0.0)) >= 0.7
                     and float(fsnap.get("substitutability", 1.0)) <= 0.4)
        for pol in self.projection.matching({"SHADOW"}):
            agrees = qualifies if decision["action_name"] == "purchase" else True
            self.runtime.emit(Ev.POLICY_SHADOW_EVALUATED,
                              {"policy_id": pol["id"], "decision_id": decision["id"],
                               "agrees": agrees},
                              Actor.SYSTEM)
            # the projection has already applied the event synchronously
            if pol.get("agreements", 0) >= self.config.policy_activation_agreements:
                self.runtime.emit(Ev.POLICY_UPDATED,
                                  {"policy_id": pol["id"],
                                   "changes": {"status": "ACTIVE"}},
                                  Actor.SYSTEM)

    def seed(self, description: str, signature: str | None = None) -> dict:
        policy = {
            "id": self.runtime.next_id("polseed"),
            "description": description,
            "status": "ACTIVE",
            "features_signature": signature,
            "applicable_context": {"domain": "general"},
            "evidence_count": 0,
            "agreements": 0,
            "provenance": "seed",
        }
        self.runtime.emit(Ev.POLICY_CREATED, {"policy": policy}, Actor.HUMAN)
        return policy
