"""Phase 3: counterfactuals, recurrence advisories, contradictions,
calibrated priors, graph hygiene, compensation."""
from __future__ import annotations

from pgdca.domain import RelType, ValidationStatus, edge
from pgdca.events import Actor, Ev
from pgdca.scenario.toy import ToyEnvironment, create
from tests.conftest import drive, events_of


# ----------------------------------------------------------- counterfactual
def test_counterfactual_regret_and_avoidability(ctrl_env):
    ctrl, _ = ctrl_env
    drive(ctrl)
    failed = next(r for r in ctrl.journal.records.values()
                  if (r.get("execution") or {}).get("status") == "failed")
    cf = failed["counterfactual"]
    assert cf["estimate"] is True
    assert cf["regret"] > 0
    # the helmet purchase was the best-scored option: bad luck, not bad judgment
    assert cf["avoidable"] is False
    ok = next(r for r in ctrl.journal.records.values()
              if r["decision"]["params"].get("factor_id") == "boots"
              and r["decision"]["action_name"] == "purchase")
    assert ok["counterfactual"]["regret"] == 0.0
    assert events_of(ctrl, Ev.COUNTERFACTUAL_ANALYZED.value)


# ------------------------------------------------------------ contradictions
def test_advert_claim_contradicted_by_market_observation(ctrl_env):
    ctrl, _ = ctrl_env
    drive(ctrl, inject_after_first_approval=True)
    snap = ctrl.evidence_store.snapshot()
    claims = [c for c in snap["claims"] if c["subject"] == "fruit"]
    assert claims and claims[0]["trust"] == "external"
    assert claims[0]["value"] == 0.5
    contras = [c for c in snap["contradictions"] if c["subject"] == "fruit"]
    assert contras, "market research must contradict the advert claim"
    c = contras[0]
    assert c["claim_a"]["value"] == 0.5 and c["claim_b"]["value"] == 2.0
    assert c["status"] == "RESOLVED_B"   # observed beats external claim
    assert events_of(ctrl, Ev.CONTRADICTION_DETECTED.value)


def test_contradiction_resolution_is_human_only(ctrl_env):
    ctrl, _ = ctrl_env
    drive(ctrl, inject_after_first_approval=True)
    cid = ctrl.evidence_store.snapshot()["contradictions"][0]["id"]
    try:
        ctrl.evidence.resolve(cid, "CONTEXT_DEPENDENT", Actor.SYSTEM)
        raise AssertionError("system must not resolve contradictions")
    except PermissionError:
        pass
    ctrl.evidence.resolve(cid, "CONTEXT_DEPENDENT", Actor.HUMAN, "verified both")
    assert (ctrl.evidence_store.contradictions[cid]["status"]
            == "CONTEXT_DEPENDENT")


# --------------------------------------------------------- calibrated priors
def test_claims_shrink_toward_observed_rate(ctrl_env):
    ctrl, _ = ctrl_env
    ctrl.self_model.actions["procurement/purchase"] = {"attempts": 4, "successes": 1}
    p = ctrl.self_model.calibrated_success("procurement", "purchase", 0.9)
    assert abs(p - (0.9 * 3 + 1) / (3 + 4)) < 1e-3   # ~0.5286 (rounded to 4dp)
    assert ctrl.self_model.calibrated_success("procurement", "purchase", 0.9) < 0.9
    assert ctrl.self_model.calibrated_success("other", "purchase", 0.9) == 0.9


def test_loop_uses_calibrated_priors(ctrl_env):
    ctrl, _ = ctrl_env
    drive(ctrl)
    # after the helmet failure, later purchase decisions carry a probability
    # below the LLM's claimed 0.9, with the claim preserved for audit
    fruit = next(r for r in ctrl.journal.records.values()
                 if r["decision"]["params"].get("factor_id") == "fruit"
                 and r["decision"]["action_name"] == "purchase")
    d = fruit["decision"]
    assert d["params"]["claimed_success_prob"] == 0.9
    assert d["success_prob"] < 0.9


# ------------------------------------------------------ recurrence advisory
def test_recurrence_advisory_appears_on_verdict(ctrl_env):
    ctrl, _ = ctrl_env
    sig = ('{"action": "purchase", "budget_constrained": true, '
           '"picked_high_importance_low_subst": true}')
    ctrl.self_model.signature_outcomes[sig] = {"success": 0, "failure": 2}
    drive(ctrl)
    boots = next(r for r in ctrl.journal.records.values()
                 if r["decision"]["params"].get("factor_id") == "boots"
                 and r["decision"]["action_name"] == "purchase")
    assert any("[advisory]" in x and "previously failed" in x
               for x in boots["verdict"]["reasons"])


# ------------------------------------------------------------- graph hygiene
def test_macro_cycle_prunes_stale_hypothesized_edges(ctrl_env):
    ctrl, _ = ctrl_env
    ctrl.runtime.emit(Ev.EDGE_ADDED, {"edge": edge(
        "e_wild_guess", "fruit", "diet", RelType.CAUSES,
        ValidationStatus.HYPOTHESIZED, "model_inference",
        importance=0.3, confidence=0.4)}, Actor.SYSTEM)
    drive(ctrl)
    while ctrl.cycle < ctrl.config.macro_interval_cycles:
        ctrl.step()
    maint = events_of(ctrl, Ev.GRAPH_MAINTENANCE.value)
    assert maint and "e_wild_guess" in maint[0].payload["pruned_edges"]
    assert ctrl.graph.edges["e_wild_guess"]["validity_status"] == "INVALIDATED"
    # validated design edges survive
    assert ctrl.graph.edges["e_b_summit"]["validity_status"] == "ACTIVE"


# -------------------------------------------------------------- compensation
def test_revoking_executed_purchase_triggers_compensation(ctrl_env):
    ctrl, env = ctrl_env
    for _ in range(10):
        r = ctrl.run(10)[-1]
        if r.status == "waiting_human":
            break
    ctrl.resolve_pending(True, "approve boots")
    assert ctrl.budgets.snapshot()["money"]["spent"] == 400.0

    boots = next(r for r in ctrl.journal.records.values()
                 if r["decision"]["params"].get("factor_id") == "boots"
                 and r["decision"]["action_name"] == "purchase")
    out = ctrl.override_verdict(boots["verdict"]["id"], approve=False,
                                note="changed my mind")
    assert out["compensated"] is True
    assert ctrl.budgets.snapshot()["money"]["spent"] == 0.0
    assert ctrl.graph.node("boots")["props"]["acquired_qty"] == 0
    assert env.refunds and env.refunds[0]["refunded"] == 400.0
    assert events_of(ctrl, Ev.COMPENSATION_EXECUTED.value)
    assert boots["compensation"]["tool"] == "compensate.purchase"


def test_repeated_environment_failures_accumulate_recurrence():
    env = ToyEnvironment(fail_once=(), fail_times={"helmet": 3})
    ctrl, _ = create(env=env)
    drive(ctrl)
    rec = ctrl.self_model.snapshot()["recurrence"]
    assert any(v["failure"] >= 2 for v in rec.values())
