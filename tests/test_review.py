"""Phase 8 / M29: cross-AI review - granular matrix, consensus rounds,
withdrawal, disagreement overrides (human vs primary_decides)."""
from __future__ import annotations

from pgdca.cognition.mock_llm import MockReviewerAdapter
from pgdca.events import Actor, Ev
from pgdca.scenario.toy import create
from tests.conftest import drive, events_of


def _enable(ctrl, checkpoint, max_rounds=2, on_disagreement="human"):
    matrix = dict(ctrl.config.review_matrix)
    matrix[checkpoint] = dict(matrix.get(checkpoint, {}), enabled=True,
                              max_rounds=max_rounds,
                              on_disagreement=on_disagreement)
    ctrl.update_config({"review_matrix": matrix}, Actor.HUMAN)


def _purchase_rec(ctrl, fid):
    return next(r for r in ctrl.journal.records.values()
                if r["decision"]["params"].get("factor_id") == fid
                and r["decision"]["action_name"] == "purchase")


# ----------------------------------------------------------- optionality
def test_review_is_off_by_default(ctrl_env):
    ctrl, _ = ctrl_env
    drive(ctrl)
    assert events_of(ctrl, Ev.REVIEW_COMPLETED.value) == []


def test_matrix_is_granular_per_checkpoint(ctrl_env):
    ctrl, _ = ctrl_env
    _enable(ctrl, "retrospective", max_rounds=1,
            on_disagreement="primary_decides")
    drive(ctrl)
    checkpoints = {r["checkpoint"] for r in ctrl.reviews.snapshot()}
    assert checkpoints == {"retrospective"}   # decision/strategy untouched


# ------------------------------------------------------------ consensus
def test_consensus_through_defense_rounds(ctrl_env):
    ctrl, _ = ctrl_env
    _enable(ctrl, "decision")
    drive(ctrl)
    boots = _purchase_rec(ctrl, "boots")
    rv = boots["reviews"][0]
    # round 1: high-cost objection; primary defends with importance;
    # round 2: reviewer agrees
    assert rv["outcome"] == "consensus" and rv["rounds"] == 2
    assert rv["messages"][0]["objections"][0]["type"] == "high_cost"
    assert "importance" in rv["messages"][1]["maintained"][0]["evidence"]
    helmet = _purchase_rec(ctrl, "helmet")
    assert helmet["reviews"][0]["rounds"] == 1   # cheap: first-round agree
    assert boots.get("execution")                # consensus -> enacted
    # review calls are cost-accounted like all cognition
    usage = ctrl.llm_usage.snapshot()
    assert usage["review"]["calls"] > 0 and usage["defend"]["calls"] > 0


# --------------------------------------------------------- disagreement
def test_no_consensus_goes_to_the_human(ctrl_env):
    ctrl, _ = create(reviewer=MockReviewerAdapter(stubborn=("helmet",)))
    _enable(ctrl, "decision", max_rounds=2, on_disagreement="human")
    drive(ctrl)
    helmet = _purchase_rec(ctrl, "helmet")
    rv = helmet["reviews"][0]
    assert rv["outcome"] == "disagreement_human" and rv["rounds"] == 2
    assert any(x.startswith("[review] no cross-AI consensus")
               for x in helmet["verdict"]["reasons"])
    assert helmet["verdict"]["status"] == "HUMAN_REQUIRED"
    # the human approved, so the action was enacted (this first attempt
    # hits the scenario's scripted stockout; a later retry succeeds)
    assert helmet["execution"] is not None
    assert any(r["decision"]["params"].get("factor_id") == "helmet"
               and (r.get("execution") or {}).get("status") == "ok"
               for r in ctrl.journal.records.values())


def test_no_consensus_primary_decides_with_agreed_points(ctrl_env):
    ctrl, _ = create(reviewer=MockReviewerAdapter(stubborn=("helmet",)))
    _enable(ctrl, "decision", max_rounds=2, on_disagreement="primary_decides")
    drive(ctrl)
    helmet = _purchase_rec(ctrl, "helmet")
    rv = helmet["reviews"][0]
    assert rv["outcome"] == "disagreement_primary"
    final = rv["messages"][-1]
    assert final.get("final") and "final decision by the primary" in final["text"]
    assert rv["standing_objections"][0]["type"] == "stubborn"
    assert helmet["verdict"]["status"] == "GRANTED"
    assert any("reviewer dissent recorded" in x
               for x in helmet["verdict"]["reasons"])
    # consensus points agreed on other decisions accumulate per checkpoint
    assert ctrl.reviews.agreed_points.get("decision")


def test_primary_concession_withdraws_the_decision():
    ctrl, env = create(reviewer=MockReviewerAdapter(withdraw=("fruit",)))
    _enable(ctrl, "decision")
    drive(ctrl)
    assert not any(p["factor_id"] == "fruit" for p in env.purchases)
    pruned = [e for e in events_of(ctrl, Ev.HYPOTHESIS_PRUNED.value)
              if "conceded" in e.payload.get("reason", "")]
    assert pruned
    assert any(r["outcome"] == "withdrawn" for r in ctrl.reviews.snapshot())


# --------------------------------------------------------------- strategy
def test_strategy_disagreement_defers_and_pauses_replanning():
    ctrl, _ = create(reviewer=MockReviewerAdapter(stubborn=("str_1",)))
    _enable(ctrl, "strategy", max_rounds=1, on_disagreement="human")
    drive(ctrl)
    assert ctrl.strategies.branches["str_1"]["status"] == "DEFERRED"
    th = next(t for t in ctrl.deliberations.snapshot()
              if (t["messages"][0].get("packet") or {})
              .get("checkpoint") == "strategy")
    assert th["opened_by"] == "system" and th["status"] == "OPEN"
    assert ctrl._strategy_review_hold() is True
    # no branch was re-selected while the hold stood; the loop still
    # carried the scenario through pure arbitration
    assert not any(b["status"] == "ACTIVE" for b in ctrl.strategies.snapshot())
    ctrl.resolve_deliberation(th["id"], "confirmed", "discussed, proceed")
    assert ctrl._strategy_review_hold() is False


# ----------------------------------------------------------- retrospective
def test_contested_retrospective_blocks_policy_learning(ctrl_env):
    ctrl, _ = ctrl_env
    _enable(ctrl, "retrospective", max_rounds=1, on_disagreement="human")
    learned = []
    orig = ctrl.policy_engine.learn
    ctrl.policy_engine.learn = lambda p: (learned.append(p["decision_id"]),
                                          orig(p))[1]
    drive(ctrl)
    failed = next(r for r in ctrl.journal.records.values()
                  if (r.get("execution") or {}).get("status") == "failed")
    rv = failed["reviews"][0]
    assert rv["outcome"] == "disagreement_human"
    assert rv["standing_objections"][0]["type"] == "contest_luck"
    assert failed["decision_id"] not in learned      # learning skipped
    ok = _purchase_rec(ctrl, "boots")
    assert ok["decision_id"] in learned              # others still learn
    th = next(t for t in ctrl.deliberations.snapshot()
              if (t["messages"][0].get("packet") or {})
              .get("checkpoint") == "retrospective")
    assert failed["decision_id"] in th["messages"][0]["text"]


def test_uncontested_retrospective_in_primary_mode_still_learns(ctrl_env):
    ctrl, _ = ctrl_env
    _enable(ctrl, "retrospective", max_rounds=1,
            on_disagreement="primary_decides")
    learned = []
    orig = ctrl.policy_engine.learn
    ctrl.policy_engine.learn = lambda p: (learned.append(p["decision_id"]),
                                          orig(p))[1]
    drive(ctrl)
    failed = next(r for r in ctrl.journal.records.values()
                  if (r.get("execution") or {}).get("status") == "failed")
    assert failed["reviews"][0]["outcome"] == "disagreement_primary"
    assert failed["decision_id"] in learned   # dissent recorded, learning on
