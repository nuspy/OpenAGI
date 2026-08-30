"""Phase 8 / M30: RAG ground-check inside the guardrail system."""
from __future__ import annotations

import pytest

from pgdca.events import Actor
from pgdca.security.guardrails import Flexibility, guardrail
from pgdca.security.supervisor import RiskClass
from tests.conftest import drive


def _ground_guardrail(require_evidence=False):
    return guardrail(
        "claims must match grounded facts", tier=1,
        rule={"kind": "ground_check", "attributes": ["unit_cost"],
              "tolerance": 0.15, "require_evidence": require_evidence},
        flexibility=Flexibility.SOFT_BLOCK,
        conditions={"risk_class_at_least": RiskClass.FINANCIAL.value},
        id="t1_ground")


def test_observations_auto_index_as_grounded_facts(ctrl_env):
    ctrl, _ = ctrl_env
    drive(ctrl)
    g = ctrl.grounding.grounded_value("boots", "unit_cost")
    assert g and g["value"] == 400.0 and g["source"] == "market"
    hits = ctrl.grounding.retrieve("boots unit_cost")
    assert hits and hits[0]["meta"]["factor_id"] == "boots"


def test_knowledge_documents_are_human_only(ctrl_env):
    ctrl, _ = ctrl_env
    with pytest.raises(PermissionError):
        ctrl.add_knowledge("fake fact", None, actor=Actor.SYSTEM)
    kid = ctrl.add_knowledge(
        "fruit market price is 2.0 per unit",
        {"factor_id": "fruit", "attribute": "unit_cost", "value": 2.0,
         "source": "human"})
    assert kid.startswith("kb_")
    assert ctrl.grounding.grounded_value("fruit", "unit_cost")["value"] == 2.0


def test_ground_check_catches_the_advert_lie(ctrl_env):
    """The fake price contradicts curated knowledge - flagged with no
    LLM in the loop, independently of the taint defense."""
    ctrl, _ = ctrl_env
    ctrl.add_knowledge("fruit market price is 2.0",
                       {"factor_id": "fruit", "attribute": "unit_cost",
                        "value": 2.0, "source": "human"})
    ctrl.guardrails.create(_ground_guardrail(), Actor.HUMAN)
    drive(ctrl, inject_after_first_approval=True)
    injected = next(r for r in ctrl.journal.records.values()
                    if r["decision"].get("derived_from"))
    reasons = " | ".join(injected["verdict"]["reasons"])
    assert "contradicts grounded value 2.0" in reasons
    assert injected["verdict"]["status"] == "HUMAN_REQUIRED"
    assert injected.get("execution") is None       # denied by the human


def test_require_evidence_flags_ungrounded_claims(ctrl_env):
    ctrl, _ = ctrl_env
    ctrl.guardrails.create(_ground_guardrail(require_evidence=True),
                           Actor.HUMAN)
    drive(ctrl, inject_after_first_approval=True)
    injected = next(r for r in ctrl.journal.records.values()
                    if r["decision"].get("derived_from"))
    assert "no grounding evidence" in " | ".join(injected["verdict"]["reasons"])


def test_grounded_purchases_pass_clean(ctrl_env):
    ctrl, _ = ctrl_env
    ctrl.guardrails.create(_ground_guardrail(require_evidence=True),
                           Actor.HUMAN)
    drive(ctrl)
    boots = next(r for r in ctrl.journal.records.values()
                 if r["decision"]["params"].get("factor_id") == "boots"
                 and r["decision"]["action_name"] == "purchase")
    # researched price == grounded observation: the guardrail stays silent
    assert not any("t1_ground" == t for t in boots["verdict"]["triggered"])
    assert boots["execution"]["status"] == "ok"
