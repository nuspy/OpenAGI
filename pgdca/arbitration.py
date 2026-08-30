"""Multi-objective arbitration: the canonical decision-value function.

U(a) = sum_i [ w_i * p_i(a) * dV_i(a) ] - C(a) - R(a) - OC(a) + IG(a) + CG(a)
(normative form: Appendix A of the implementation specification).

Includes the sensitivity gate of the calibrated-scoring discipline: if
the ranking flips when low-confidence inputs are perturbed, the
decision is not mature - prefer information gain or escalate.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .cognition.gateway import Hypothesis
from .config import Config
from .graph import GraphProjection
from .security.budgets import BudgetProjection


@dataclass
class Scored:
    hyp: Hypothesis
    utility: float
    parts: dict = field(default_factory=dict)
    utility_pessimistic: float = 0.0
    utility_optimistic: float = 0.0


def _goal_contribution(graph: GraphProjection, factor_id: str, success_prob: float) -> tuple[float, float, dict]:
    """Sum over affected goals of priority * p * signed effect * path confidence."""
    total, min_conf, detail = 0.0, 1.0, {}
    for goal_id, d in graph.goal_effects(factor_id).items():
        goal = graph.node(goal_id)
        if goal is None or goal["status"] != "ACTIVE":
            continue
        w = float(goal["props"].get("priority", 0.5))
        term = w * success_prob * d["effect"] * d["confidence"]
        total += term
        min_conf = min(min_conf, d["confidence"])
        detail[goal_id] = round(term, 4)
    return total, min_conf, detail


def score_candidates(graph: GraphProjection, budgets: BudgetProjection,
                     hyps: list[Hypothesis], config: Config,
                     resource: str = "money") -> tuple[list[Scored], bool]:
    """Rank hypotheses by U(a); returns (ranked, sensitivity_unstable)."""
    limit = max(budgets.limit(resource), 1.0)
    remaining = budgets.remaining(resource)
    scored: list[Scored] = []

    # first pass: gross contributions (needed for opportunity cost)
    gross: dict[int, float] = {}
    for i, h in enumerate(hyps):
        if h.action_name == "purchase":
            # real models sometimes omit factor_id: contribution 0, not a crash
            c, _, _ = _goal_contribution(graph, h.params.get("factor_id", ""),
                                         h.success_prob)
            gross[i] = c
        else:
            gross[i] = 0.0

    for i, h in enumerate(hyps):
        parts: dict = {}
        cost = float(h.params.get("total_cost", 0.0))
        cost_conf = float(h.params.get("cost_confidence", h.confidence))
        if h.action_name == "purchase":
            contribution, path_conf, detail = _goal_contribution(
                graph, h.params.get("factor_id", ""), h.success_prob)
            parts["goal_contributions"] = detail
            ig = 0.0
        else:  # information-gathering actions
            contribution, path_conf = 0.0, 1.0
            f = graph.node(h.params.get("factor_id", "")) or {"props": {}}
            unc = 1.0 - float(f["props"].get("cost_confidence", 0.3))
            imp = float(f["props"].get("importance", 0.5))
            ig = unc * imp * config.ig_weight

        cost_norm = cost / limit
        risk = (1.0 - h.success_prob) * cost_norm * config.risk_weight
        unaffordable = config.unaffordable_penalty if cost > remaining else 0.0

        # opportunity cost: choosing a starves a better, currently affordable b
        oc = 0.0
        if h.action_name == "purchase" and cost <= remaining:
            for j, other in enumerate(hyps):
                if j == i or other.action_name != "purchase":
                    continue
                ocost = float(other.params.get("total_cost", 0.0))
                if ocost <= remaining and ocost > remaining - cost and gross[j] > gross[i]:
                    oc = max(oc, (gross[j] - gross[i]) * config.oc_weight)

        u = contribution + ig - cost_norm * config.cost_weight - risk - oc - unaffordable
        parts.update({"contribution": round(contribution, 4), "ig": round(ig, 4),
                      "cost_norm": round(cost_norm, 4), "risk": round(risk, 4),
                      "oc": round(oc, 4), "unaffordable": unaffordable,
                      "cost_confidence": cost_conf, "path_confidence": round(path_conf, 4)})

        # adversarial bounds for the sensitivity gate
        p = config.perturbation
        u_pess, u_opt = u, u
        if cost_conf < config.low_confidence_threshold and cost > 0:
            delta = (cost * p / limit) * (config.cost_weight + (1 - h.success_prob))
            u_pess -= delta
            u_opt += delta
        if path_conf < config.low_confidence_threshold and contribution != 0:
            u_pess -= abs(contribution) * p
            u_opt += abs(contribution) * p
        scored.append(Scored(h, u, parts, u_pess, u_opt))

    ranked = sorted(scored, key=lambda s: (-s.utility, s.hyp.action_name,
                                           str(sorted(s.hyp.params.items()))))
    unstable = False
    if len(ranked) >= 2:
        best = ranked[0]
        unstable = any(o.utility_optimistic > best.utility_pessimistic
                       and o is not best for o in ranked[1:])
    return ranked, unstable
