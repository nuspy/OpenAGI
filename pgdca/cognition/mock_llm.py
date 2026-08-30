"""Deterministic mock adapter for the LLM port.

Implements plausible-but-fallible generative behavior on structured
context: it proposes research for unknown costs, purchases for known
ones - and it is deliberately naive about untrusted external content
(it will propose acting on an embedded "offer"), because catching that
is the architecture's job (taint + supervisor), not the model's.
"""
from __future__ import annotations

import re

from .gateway import SCHEMA_VERSION
from ..security.supervisor import RiskClass

OFFER_RE = re.compile(r"OFFER\s+(\w+)\s+([\d.]+)")


class MockLlmAdapter:
    def generate(self, request: dict) -> dict:
        role = request.get("role")
        ctx = request.get("context", {})
        if role == "hypotheses":
            return self._hypotheses(ctx)
        if role == "critique":
            return self._critique(ctx)
        if role == "abstraction":
            return self._abstraction(ctx)
        return {"schema": SCHEMA_VERSION, "role": role or "unknown",
                "summary": "no-op", "hypotheses": []}

    # ------------------------------------------------------------------
    def _hypotheses(self, ctx: dict) -> dict:
        hyps: list[dict] = []
        factors = sorted(ctx.get("factors", []),
                         key=lambda f: (-float(f.get("importance", 0.5)), f["id"]))
        for f in factors:
            needed = int(f.get("quantity_needed", 1)) - int(f.get("acquired_qty", 0))
            if needed <= 0:
                continue
            cost = f.get("unit_cost")
            conf = float(f.get("cost_confidence", 0.3))
            if cost is None or conf < 0.6:
                hyps.append({
                    "action_name": "research_price",
                    "params": {"factor_id": f["id"], "domain": "procurement"},
                    "rationale": f"cost of {f['id']} is uncertain; reduce uncertainty first",
                    "expected": {"cost_known": f["id"]},
                    "success_prob": 0.95, "confidence": 0.9,
                    "risk_class": RiskClass.READ_ONLY.value,
                })
            else:
                hyps.append({
                    "action_name": "purchase",
                    "params": {"factor_id": f["id"], "quantity": needed,
                               "unit_cost": float(cost), "total_cost": float(cost) * needed,
                               "cost_confidence": conf, "domain": "procurement"},
                    "rationale": f"acquire {f['id']} to satisfy its target",
                    "expected": {"factor_acquired": f["id"], "quantity": needed,
                                 "total_cost": float(cost) * needed},
                    "success_prob": 0.9, "confidence": 0.85,
                    "risk_class": RiskClass.FINANCIAL.value,
                })
        # naive incorporation of external content (data treated as opportunity)
        for c in ctx.get("external_content", []):
            for factor_id, price in OFFER_RE.findall(c.get("text", "")):
                match = [f for f in factors if f["id"] == factor_id]
                if not match:
                    continue
                f = match[0]
                needed = int(f.get("quantity_needed", 1)) - int(f.get("acquired_qty", 0))
                if needed <= 0:
                    continue
                hyps.append({
                    "action_name": "purchase",
                    "params": {"factor_id": factor_id, "quantity": needed,
                               "unit_cost": float(price), "total_cost": float(price) * needed,
                               "cost_confidence": 0.9, "domain": "procurement"},
                    "rationale": f"special offer found for {factor_id} at {price}",
                    "expected": {"factor_acquired": factor_id, "quantity": needed,
                                 "total_cost": float(price) * needed},
                    "success_prob": 0.9, "confidence": 0.9,
                    "risk_class": RiskClass.FINANCIAL.value,
                    "derived_from": [c["id"]],
                })
        assumptions = []
        skills = ctx.get("skills", [])
        if skills:  # skills are data informing the proposal, never commands
            assumptions.append("applied skills: "
                               + ", ".join(s["name"] for s in skills))
        return {"schema": SCHEMA_VERSION, "role": "hypotheses",
                "summary": f"{len(hyps)} candidate actions",
                "hypotheses": hyps, "assumptions": assumptions, "risks": [],
                "missing_information": [f["id"] for f in factors
                                        if f.get("unit_cost") is None],
                "confidence": 0.8}

    def _critique(self, ctx: dict) -> dict:
        risks = []
        hyp_factors = {h.get("params", {}).get("factor_id")
                       for h in ctx.get("hypotheses", [])}
        for a in ctx.get("antagonisms", []):
            if a["factor"] in hyp_factors:
                risks.append({"type": "cross_goal_conflict", "factor": a["factor"],
                              "supports": a["supports"], "harms": a["harms"]})
        missing = [h["params"]["factor_id"] for h in ctx.get("hypotheses", [])
                   if h.get("params", {}).get("cost_confidence", 1.0) < 0.6]
        return {"schema": SCHEMA_VERSION, "role": "critique",
                "summary": f"{len(risks)} conflicts flagged",
                "hypotheses": [], "assumptions": [], "risks": risks,
                "missing_information": missing, "confidence": 0.85}

    def _abstraction(self, ctx: dict) -> dict:
        feats = ctx.get("features", {})
        if feats.get("budget_constrained") and feats.get("picked_high_importance_low_subst"):
            text = ("Under constrained resources, prioritize high-impact, "
                    "non-substitutable enabling factors over low-impact "
                    "substitutable support factors.")
        else:
            text = "Prefer actions with verified costs and positive multi-goal utility."
        return {"schema": SCHEMA_VERSION, "role": "abstraction",
                "summary": text, "hypotheses": [], "assumptions": [],
                "risks": [], "missing_information": [], "confidence": 0.8}
