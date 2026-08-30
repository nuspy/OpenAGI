"""LLM gateway (validation, repair, conformance) and arbitration."""
from __future__ import annotations

import pytest

from pgdca.arbitration import score_candidates
from pgdca.cognition.gateway import (GatewayError, Hypothesis, LlmGateway,
                                     SCHEMA_VERSION, run_conformance)
from pgdca.cognition.mock_llm import MockLlmAdapter
from pgdca.config import Config
from pgdca.events import Actor, Ev  # noqa: F401 - Actor used in tests
from pgdca.security.supervisor import RiskClass
from tests.conftest import events_of


# --------------------------------------------------------------- gateway
class RepairableAdapter:
    """Returns garbage first, valid output when asked to repair."""

    def generate(self, request):
        if "repair" in request:
            return {"schema": SCHEMA_VERSION, "role": request["role"],
                    "summary": "repaired", "hypotheses": []}
        return {"nonsense": True}


class BrokenAdapter:
    def generate(self, request):
        return {"nonsense": True}


def test_gateway_repair_loop(ctrl_env):
    ctrl, _ = ctrl_env
    gw = LlmGateway(ctrl.runtime, RepairableAdapter(), Config())
    resp = gw.ask("hypotheses", {})
    assert resp.summary == "repaired"
    reqs = events_of(ctrl, Ev.LLM_REQUEST.value)
    assert len(reqs) >= 2 and "repair" in reqs[-1].payload["request"]


def test_gateway_fails_loudly_after_repairs(ctrl_env):
    ctrl, _ = ctrl_env
    gw = LlmGateway(ctrl.runtime, BrokenAdapter(), Config())
    with pytest.raises(GatewayError):
        gw.ask("hypotheses", {})
    assert events_of(ctrl, Ev.ERROR_DETECTED.value)


def test_mock_adapter_conformance():
    samples = [
        {"role": "hypotheses", "context": {"factors": [], "goals": []}},
        {"role": "critique", "context": {"hypotheses": [], "antagonisms": []}},
        {"role": "abstraction", "context": {"features": {}}},
    ]
    assert run_conformance(MockLlmAdapter(), samples) == []


# ----------------------------------------------------------- arbitration
def _purchase(factor_id, total_cost, conf=0.95, p=0.9):
    return Hypothesis(action_name="purchase",
                      params={"factor_id": factor_id, "quantity": 1,
                              "total_cost": total_cost, "cost_confidence": conf,
                              "domain": "procurement"},
                      success_prob=p, confidence=conf,
                      risk_class=RiskClass.FINANCIAL.value)


def test_cross_goal_antagonism_lowers_utility(ctrl_env):
    ctrl, _ = ctrl_env
    # bars support the summit but antagonize the diet; fruit does not.
    ctrl.human_edit_node("diet", {"priority": 0.9}, Actor.HUMAN)
    ranked, _ = score_candidates(
        ctrl.graph, ctrl.budgets,
        [_purchase("bars", 20.0), _purchase("fruit", 20.0)], ctrl.config)
    assert ranked[0].hyp.params["factor_id"] == "fruit"
    bars = next(s for s in ranked if s.hyp.params["factor_id"] == "bars")
    assert bars.parts["goal_contributions"].get("diet", 0) < 0


def test_opportunity_cost_prioritizes_critical_enabler(ctrl_env):
    ctrl, _ = ctrl_env
    ctrl.set_budget("money", 420, Actor.HUMAN)
    ranked, _ = score_candidates(
        ctrl.graph, ctrl.budgets,
        [_purchase("bars", 200.0), _purchase("boots", 400.0)], ctrl.config)
    assert ranked[0].hyp.params["factor_id"] == "boots"
    bars = next(s for s in ranked if s.hyp.params["factor_id"] == "bars")
    assert bars.parts["oc"] > 0  # buying bars would starve the boots


def test_unaffordable_candidate_is_dominated(ctrl_env):
    ctrl, _ = ctrl_env
    ranked, _ = score_candidates(
        ctrl.graph, ctrl.budgets, [_purchase("boots", 900.0)], ctrl.config)
    assert ranked[0].parts["unaffordable"] > 0
    assert ranked[0].utility < 0


def test_sensitivity_gate_flags_low_confidence_ties(ctrl_env):
    ctrl, _ = ctrl_env
    # near-tie between two routes to the same factor; one has uncertain cost
    a = _purchase("fruit", 20.0, conf=0.3)
    b = _purchase("fruit", 22.0, conf=0.95)
    _, unstable = score_candidates(ctrl.graph, ctrl.budgets, [a, b], ctrl.config)
    assert unstable is True

    _, unstable2 = score_candidates(
        ctrl.graph, ctrl.budgets,
        [_purchase("boots", 400.0), _purchase("fruit", 20.0)], ctrl.config)
    assert unstable2 is False  # confident inputs, wide margin
