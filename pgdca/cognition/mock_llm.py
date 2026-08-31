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
EDIT_RE = re.compile(
    r"(importance|priority|substitutability|unit_cost)\s*(?:to|=|a)?\s*([\d.]+)")


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
        if role == "strategies":
            return self._strategies(ctx)
        if role == "deliberate":
            return self._deliberate(ctx)
        if role == "defend":
            return self._defend(ctx)
        if role == "decide":
            return self._decide(ctx)
        if role == "integrate":
            return self._integrate(ctx)
        if role == "scout":
            return self._scout(ctx)
        return {"schema": SCHEMA_VERSION, "role": role or "unknown",
                "summary": "no-op", "hypotheses": []}

    def _scout(self, ctx: dict) -> dict:
        """Deterministic scouting demo: one search, then two canned options
        (clearly placeholder) so the flow is visible without a real model."""
        if ctx.get("phase") == "search":
            return {"schema": SCHEMA_VERSION, "role": "scout",
                    "summary": "search", "hypotheses": [
                        {"action_name": "search_web",
                         "params": {"url": "https://example.test/"}}]}
        label = (ctx.get("target") or {}).get("label", "item")
        opts = [{"label": f"Opzione A per {label}", "price": 240,
                 "currency": "EUR", "merchant": "DemoShop",
                 "characteristics": "esempio (adapter mock)"},
                {"label": f"Opzione B per {label}", "price": 180,
                 "currency": "EUR", "merchant": "DemoShop",
                 "characteristics": "esempio piu' economico (mock)"}]
        return {"schema": SCHEMA_VERSION, "role": "scout", "summary": "options",
                "hypotheses": [{"action_name": "propose_option", "params": o,
                                "rationale": "demo"} for o in opts]}

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

    def _strategies(self, ctx: dict) -> dict:
        """Two competing multi-step branches over the graph-derived context
        (external content never enters strategy formation)."""
        remaining = ctx.get("budget", {}).get("money", {}).get("remaining", 0.0)
        candidates = []
        for f in ctx.get("factors", []):
            needed = int(f.get("quantity_needed", 1)) - int(f.get("acquired_qty", 0))
            if needed <= 0:
                continue
            cost = f.get("unit_cost")
            if cost is not None and float(cost) * needed > remaining:
                continue  # known-unaffordable: plan around it
            candidates.append(f)

        def steps_for(ordering):
            steps = []
            for f in ordering:
                if f.get("unit_cost") is None or float(f.get("cost_confidence", 0.3)) < 0.6:
                    steps.append({"action_name": "research_price",
                                  "factor_id": f["id"]})
                steps.append({"action_name": "purchase", "factor_id": f["id"]})
            return steps

        by_importance = sorted(candidates,
                               key=lambda f: (-float(f.get("importance", 0.5)),
                                              f["id"]))
        hyps = []
        if by_importance:
            hyps.append({"action_name": "strategy",
                         "params": {"label": "critical-enablers-first",
                                    "steps": steps_for(by_importance)},
                         "rationale": "secure high-impact, low-substitutability "
                                      "factors before support items",
                         "expected": {}, "success_prob": 0.9,
                         "confidence": 0.8, "risk_class": "READ_ONLY"})
        if len(by_importance) > 1:
            hyps.append({"action_name": "strategy",
                         "params": {"label": "support-items-first",
                                    "steps": steps_for(list(reversed(by_importance)))},
                         "rationale": "cheap support items first",
                         "expected": {}, "success_prob": 0.85,
                         "confidence": 0.7, "risk_class": "READ_ONLY"})
        return {"schema": SCHEMA_VERSION, "role": "strategies",
                "summary": f"{len(hyps)} strategy branches",
                "hypotheses": hyps, "assumptions": [], "risks": [],
                "missing_information": [], "confidence": 0.8}

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

    # ------------------------------------------------------------------
    def _deliberate(self, ctx: dict) -> dict:
        """Answer a human's question from the deterministic evidence
        packet; numeric edit proposals in the question become structured
        suggestions the human can apply by resolving as 'modified'."""
        ev = ctx.get("evidence") or {}
        subject = ctx.get("subject", {})
        q = (ctx.get("question") or "").lower()
        kind = subject.get("kind")
        lines: list[str] = []
        suggestions: list[dict] = []
        if kind == "decision" and ev.get("what"):
            v = ev.get("verdict") or {}
            fid = (ev["what"].get("params") or {}).get("factor_id", "")
            lines.append(f"Decision {subject.get('id')}: {ev['what']['action']}"
                         f" {fid} -> verdict {v.get('status', '?')}.")
            if ev.get("why"):
                lines.append(f"Rationale: {ev['why']}")
            alts = ev.get("alternatives_considered") or []
            if alts:
                lines.append("Ranked alternatives: " + "; ".join(
                    f"{a['action_name']}({a['params'].get('factor_id', '')}) "
                    f"U={a['utility']}" for a in alts[:3]))
            cf = ev.get("counterfactual")
            if cf:
                lines.append(f"Counterfactual estimate: regret {cf['regret']}, "
                             + ("avoidable." if cf["avoidable"]
                                else "not avoidable (bad luck, not bad judgment)."))
            ex = (ev.get("what_happened") or {}).get("execution")
            if ex:
                lines.append(f"Execution: {ex['status']}.")
        elif kind == "node" and ev.get("node"):
            n = ev["node"]
            p = n["props"]
            lines.append(f"{n['id']} ({n['kind']}): importance "
                         f"{p.get('importance')}, unit_cost {p.get('unit_cost')},"
                         f" acquired {p.get('acquired_qty', 0)}/"
                         f"{p.get('quantity_needed', 1)}.")
            goals = sorted((ev.get("goal_effects") or {}).keys())
            lines.append("Contributes to goals: "
                         + (", ".join(goals) if goals else "none known") + ".")
            if ev.get("decisions"):
                lines.append(f"{len(ev['decisions'])} recorded decision(s) "
                             f"touched this node.")
            m = EDIT_RE.search(q)
            if m:
                suggestions.append({
                    "action_name": "suggest_edit",
                    "params": {"node_id": n["id"],
                               "props": {m.group(1): float(m.group(2))}},
                    "rationale": "your proposal; apply it by resolving this "
                                 "thread as 'modified'",
                    "risk_class": "READ_ONLY"})
                lines.append(f"You propose {m.group(1)}={m.group(2)}: recorded "
                             f"as a suggestion; resolving as 'modified' "
                             f"applies it with human provenance.")
        elif kind == "strategy" and ev.get("steps") is not None:
            lines.append(f"Strategy {ev['id']} '{ev['label']}': status "
                         f"{ev['status']}, step "
                         f"{min(ev['step_index'], len(ev['steps']))}/"
                         f"{len(ev['steps'])}, score {ev['score']}. Resolving "
                         f"as 'cancelled' defers it and forces a replan.")
        elif kind == "escalation":
            lines.append(f"{ev.get('reason', 'I escalated.')} I need a human "
                         f"decision to proceed; budget remaining "
                         f"{ev.get('budget_remaining')}.")
        elif kind == "contradiction":
            a, b = ev.get("claim_a", {}), ev.get("claim_b", {})
            lines.append(f"Contradiction on {ev.get('subject')}."
                         f"{ev.get('attribute')}: {a.get('value')} "
                         f"({a.get('source')}) vs {b.get('value')} "
                         f"({b.get('source')}); status {ev.get('status')}.")
        elif kind == "guardrail":
            lines.append(f"Guardrail {ev.get('id')} (tier {ev.get('tier')}, "
                         f"{ev.get('flexibility')}): {ev.get('description')}; "
                         f"status {ev.get('status')}.")
        elif kind == "scenario":
            lines.append(f"Scenario: {len(ev.get('goals', []))} active "
                         f"goal(s), {len(ev.get('open_targets', []))} open / "
                         f"{len(ev.get('deferred_targets', []))} deferred "
                         f"target(s); budget "
                         f"{(ev.get('budget') or {}).get('remaining')} of "
                         f"{(ev.get('budget') or {}).get('limit')} remaining; "
                         f"{len(ev.get('directives', []))} directive(s), "
                         f"{len(ev.get('facts', []))} fact(s) active.")
            m = re.search(r"budget\s+(?:to|a)\s+([\d.]+)", q)
            if m:
                suggestions.append({
                    "action_name": "suggest_edit",
                    "params": {"ops": [{"op": "set_budget", "name": "money",
                                        "limit": float(m.group(1))}]},
                    "rationale": "apply by resolving as 'modified' with this "
                                 "change-set (budget moves are human-only)",
                    "risk_class": "READ_ONLY"})
                lines.append(f"You propose moving the money budget to "
                             f"{m.group(1)}: recorded as a change-set "
                             f"suggestion.")
        if not lines:
            lines.append("No structured evidence is available for this subject.")
        return {"schema": SCHEMA_VERSION, "role": "deliberate",
                "summary": " ".join(lines), "hypotheses": suggestions,
                "assumptions": [], "risks": [], "missing_information": [],
                "confidence": 0.85}

    _STOP = {"the", "a", "an", "of", "to", "and", "for", "with", "in", "on",
             "two", "weeks", "week", "my", "me", "di", "la", "il", "le", "per"}

    def _integrate(self, ctx: dict) -> dict:
        """Weave an exogenous node against the existing graph: lexical,
        deterministic. 'avoid/no/without X' proposes BLOCK edges (+
        deferral) toward matching targets; token overlap with a goal
        proposes a SUPPORT edge; target-type directives spawn a plan
        subtarget; budget words yield a budget note."""
        n = ctx.get("node", {})
        g = ctx.get("graph", {})
        props = n.get("props", {})
        text = f"{n.get('label', '')} {props.get('description', '')}".lower()
        tokens = set(re.findall(r"[a-z0-9]+", text)) - self._STOP
        weight = float(props.get("priority", props.get("importance", 0.5)))
        hyps: list[dict] = []
        risks: list[dict] = []
        missing: list[str] = []

        avoid = {m.group(1) for m in re.finditer(
            r"(?:avoid|no|without|evita|niente|senza)\s+([a-z0-9]+)", text)}
        for t in g.get("targets", []):
            ttok = (set(re.findall(r"[a-z0-9]+", t["label"].lower()))
                    | {t["id"].lower()})
            if avoid & ttok:
                hyps.append({"action_name": "propose_edge",
                             "params": {"src": n.get("id"), "dst": t["id"],
                                        "type": "BLOCK", "importance": weight,
                                        "confidence": 0.8},
                             "rationale": f"'{n.get('label')}' asks to avoid "
                                          f"'{t['label']}'"})
                hyps.append({"action_name": "propose_deferral",
                             "params": {"target_id": t["id"]},
                             "rationale": f"deferred while "
                                          f"'{n.get('label')}' is active"})
                risks.append({"type": "conflict",
                              "reason": f"blocks active target {t['id']} "
                                        f"('{t['label']}')"})
        for gl in g.get("goals", []):
            gtok = set(re.findall(r"[a-z0-9]+", gl["label"].lower())) - self._STOP
            if tokens & gtok:
                hyps.append({"action_name": "propose_edge",
                             "params": {"src": n.get("id"), "dst": gl["id"],
                                        "type": "SUPPORT",
                                        "importance": weight,
                                        "confidence": 0.7},
                             "rationale": f"'{n.get('label')}' relates to "
                                          f"goal '{gl['label']}'"})
        if (n.get("kind") == "DIRECTIVE"
                and (props.get("directive_type") == "target"
                     or tokens & {"plan", "piano"})):
            hyps.append({"action_name": "propose_target",
                         "params": {"label": f"Plan: {n.get('label')}",
                                    "priority": weight},
                         "rationale": "a directive of target type needs an "
                                      "actionable subtarget"})
        if tokens & {"budget", "money", "cost", "funds", "soldi"}:
            hyps.append({"action_name": "budget_note",
                         "params": {"note": "budget impact declared: reduce "
                                            "or reallocate other targets' "
                                            "spending room (human-only op)"},
                         "rationale": "the ratchet keeps budget moves human"})
            missing.append("amount to allocate")
        return {"schema": SCHEMA_VERSION, "role": "integrate",
                "summary": f"{len(hyps)} weaving proposal(s)",
                "hypotheses": hyps, "assumptions": [], "risks": risks,
                "missing_information": missing, "confidence": 0.75}

    def _defend(self, ctx: dict) -> dict:
        """Primary's turn in a cross-AI review round: maintained points
        stay in `risks` (with evidence), accepted objections become
        `assumptions`; conceding everything withdraws the subject."""
        context = ctx.get("review_context") or {}
        imp = (context.get("factor_snapshot") or {}).get("importance")
        maintained, agreed = [], []
        for o in ctx.get("objections", []):
            t = o.get("type")
            if t == "withdraw":
                agreed.append(f"conceded: {o.get('reason', 'objection accepted')}")
            elif t == "high_cost" and imp is not None and float(imp) >= 0.7:
                maintained.append({"type": t,
                                   "evidence": f"critical enabler: importance "
                                               f"{imp}, low substitutability"})
            elif t == "contest_luck":
                maintained.append({"type": t,
                                   "evidence": "decision quality was high; the "
                                               "alternatives scored lower ex ante"})
            elif t == "stubborn":
                maintained.append({"type": t,
                                   "evidence": "primary maintains its assessment"})
            else:
                agreed.append(f"accepted objection: {t or 'unspecified'}")
        return {"schema": SCHEMA_VERSION, "role": "defend",
                "summary": (f"{len(maintained)} point(s) maintained, "
                            f"{len(agreed)} accepted"),
                "hypotheses": [], "assumptions": agreed, "risks": maintained,
                "missing_information": [], "confidence": 0.8}

    def _decide(self, ctx: dict) -> dict:
        pts = ctx.get("agreed_points", [])
        objs = ctx.get("standing_objections", [])
        return {"schema": SCHEMA_VERSION, "role": "decide",
                "summary": (f"final decision by the primary per the review "
                            f"matrix: proceed. {len(objs)} objection(s) stand "
                            f"and are recorded as dissent; honoring "
                            f"{len(pts)} previously agreed point(s)."),
                "hypotheses": [], "assumptions": [], "risks": [],
                "missing_information": [], "confidence": 0.75}

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


class MockReviewerAdapter:
    """Deterministic second-AI reviewer for the cross-AI review port.

    Heuristics: expensive purchases draw a first-round objection that a
    good defense (high importance) resolves; audits that blame bad luck
    for a failure are contested; `stubborn` subjects never reach
    consensus (drives the disagreement paths); `withdraw` subjects draw
    an objection the primary always concedes. A real deployment swaps
    this for a different provider/model behind the same LlmPort.
    """

    def __init__(self, stubborn: tuple = (), withdraw: tuple = (),
                 high_cost_threshold: float = 300.0):
        self.stubborn = set(stubborn)
        self.withdraw = set(withdraw)
        self.high_cost_threshold = high_cost_threshold

    @staticmethod
    def _subject_key(subject: dict) -> str:
        return (subject.get("params", {}).get("factor_id")
                or subject.get("id") or subject.get("decision_id") or "")

    def generate(self, request: dict) -> dict:
        role = request.get("role")
        ctx = request.get("context", {})
        if role != "review":
            return {"schema": SCHEMA_VERSION, "role": role or "unknown",
                    "summary": "no-op", "hypotheses": []}
        subject = ctx.get("subject", {})
        checkpoint = ctx.get("checkpoint")
        key = self._subject_key(subject)
        defended = {o.get("type")
                    for m in ctx.get("exchange", [])
                    if m.get("author") == "primary"
                    for o in m.get("maintained", [])}
        objections: list[dict] = []
        if key in self.stubborn:
            objections.append({"type": "stubborn",
                               "reason": f"reviewer does not consent "
                                         f"regarding '{key}'"})
        if key in self.withdraw and "withdraw" not in defended:
            objections.append({"type": "withdraw",
                               "reason": f"reviewer asks to withdraw '{key}'"})
        if checkpoint == "decision":
            cost = float(subject.get("cost", 0.0))
            if cost >= self.high_cost_threshold and "high_cost" not in defended:
                objections.append({"type": "high_cost",
                                   "reason": f"cost {cost} deserves scrutiny "
                                             f"of cheaper alternatives"})
        elif checkpoint == "retrospective":
            audit = subject.get("audit") or {}
            cf = subject.get("counterfactual") or {}
            if (audit.get("outcome_quality", 1.0) < 0.5
                    and cf.get("avoidable") is False
                    and "contest_luck" not in defended):
                objections.append({"type": "contest_luck",
                                   "reason": "the 'bad luck' ruling deserves "
                                             "scrutiny: was the failure "
                                             "truly unavoidable?"})
        agree = not objections
        assumptions = (["agreed: high-impact spending deserves explicit "
                        "justification"]
                       if agree and ctx.get("exchange") else [])
        return {"schema": SCHEMA_VERSION, "role": "review",
                "summary": ("reviewer agrees" if agree else
                            f"reviewer raises {len(objections)} objection(s)"),
                "hypotheses": [], "assumptions": assumptions,
                "risks": objections, "missing_information": [],
                "confidence": 0.85}
