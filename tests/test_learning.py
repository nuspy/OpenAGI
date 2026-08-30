"""Audit (decision != outcome quality), policy lifecycle, calibration."""
from __future__ import annotations

from pgdca.events import Ev
from tests.conftest import drive, events_of


def test_decision_quality_is_not_outcome_quality(ctrl_env):
    ctrl, env = ctrl_env
    drive(ctrl)
    # the scripted helmet stock-out: a good decision with a bad outcome
    failed = [r for r in ctrl.journal.records.values()
              if r["decision"]["params"].get("factor_id") == "helmet"
              and (r.get("execution") or {}).get("status") == "failed"]
    assert failed, "the scripted environment failure must have occurred"
    audit = failed[0]["audit"]
    assert audit["decision_quality"] >= 0.9
    assert audit["outcome_quality"] <= 0.2
    assert audit["error_class"] == "environmental_uncertainty"
    # ... and the retry succeeded with the same decision quality
    ok = [r for r in ctrl.journal.records.values()
          if r["decision"]["params"].get("factor_id") == "helmet"
          and (r.get("execution") or {}).get("status") == "ok"]
    assert ok and ok[0]["audit"]["outcome_quality"] == 1.0


def test_policy_learned_from_recurrence_with_shadow_mode(ctrl_env):
    ctrl, _ = ctrl_env
    drive(ctrl)
    learned = [p for p in ctrl.policies.snapshot() if p["provenance"] == "learned"]
    assert learned, "recurring well-made decisions must become a policy"
    pol = learned[0]
    assert pol["status"] in ("SHADOW", "ACTIVE")
    assert pol["evidence_count"] >= ctrl.config.policy_min_evidence
    assert "non-substitutable" in pol["description"]
    assert events_of(ctrl, Ev.POLICY_SHADOW_EVALUATED.value), \
        "shadow policies must be evaluated against real decisions"
    seeds = [p for p in ctrl.policies.snapshot() if p["provenance"] == "seed"]
    assert seeds and seeds[0]["status"] == "ACTIVE"


def test_calibration_tracked_per_domain(ctrl_env):
    ctrl, _ = ctrl_env
    drive(ctrl)
    snap = ctrl.calibration.snapshot()
    assert "procurement" in snap and snap["procurement"]["samples"] >= 5
    assert events_of(ctrl, Ev.CALIBRATION_UPDATED.value)


def test_apprentice_mode_creates_restrictive_tier2_guardrail(ctrl_env):
    ctrl, _ = ctrl_env
    # fabricate poor calibration in a domain, then run the check
    ctrl.calibration.domains["procurement"] = {"sum_sq": 2.0, "n": 4}
    ctrl._apprentice_check("procurement")
    apprentice = [g for g in ctrl.guardrails.active(tier=2)
                  if g["rule"].get("kind") == "apprentice_domain"]
    assert len(apprentice) == 1
    assert apprentice[0]["provenance"] == "system_calibration"
    assert apprentice[0]["status"] == "ACTIVE"  # restrictive: self-activates
    ctrl._apprentice_check("procurement")       # idempotent
    assert len([g for g in ctrl.guardrails.active(tier=2)
                if g["rule"].get("kind") == "apprentice_domain"]) == 1
