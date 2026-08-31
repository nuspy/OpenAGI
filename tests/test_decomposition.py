"""Autonomous target decomposition with human consensus.

The owner's expected flow: a bare target ("own climbing boots") must not
sit inert - the system proposes a breakdown, ASKS the owner the branching
question (own vs buy), and weaves the answered branch into the graph only
after the human resolves the thread.
"""
from __future__ import annotations

from pgdca.cognition.gateway import SCHEMA_VERSION
from pgdca.domain import NodeKind
from pgdca.events import Actor
from pgdca.scenario.toy import create


class DecomposingAdapter:
    """Scripted: decompose proposes an owner question + two branches.
    When the conversation mentions a hard peak, it scales the breakdown up."""

    def generate(self, request):
        role = request.get("role")
        if role == "decompose":
            t = request["context"]["target"]
            convo = " ".join(m.get("text", "") for m in
                             request["context"].get("conversation", []))
            if "k2" in convo.lower():
                return {
                    "schema": SCHEMA_VERSION, "role": role,
                    "summary": "hard peak breakdown",
                    "hypotheses": [
                        {"action_name": "propose_subtarget", "params": {
                            "label": "hire a mountain guide", "priority": 0.9}},
                        {"action_name": "propose_subtarget", "params": {
                            "label": "obtain climbing permits", "priority": 0.9}},
                    ]}
            return {
                "schema": SCHEMA_VERSION, "role": role,
                "summary": f"breakdown of {t['id']}",
                "hypotheses": [
                    {"action_name": "ask_owner", "params": {
                        "question": "do we already own the climbing boots?",
                        "options": ["buy", "have"]}},
                    {"action_name": "propose_subtarget", "params": {
                        "label": "find best buys", "priority": 0.8,
                        "branch": "buy"}},
                    {"action_name": "propose_subtarget", "params": {
                        "label": "purchase after consensus", "priority": 0.7,
                        "branch": "buy"}},
                    {"action_name": "propose_subtarget", "params": {
                        "label": "verify quality with the owner",
                        "priority": 0.6, "branch": "have"}},
                ]}
        return {"schema": SCHEMA_VERSION, "role": role or "?",
                "summary": "no-op", "hypotheses": []}


def make_bare_target():
    ctrl, _ = create(adapter=DecomposingAdapter(), build=False)
    tid = ctrl.propose_goal(NodeKind.TARGET, "own climbing boots", 0.9,
                            Actor.HUMAN)
    ctrl.ratify_goal(tid, Actor.HUMAN)
    return ctrl, tid


def test_bare_target_opens_a_breakdown_thread_with_the_owner_question():
    ctrl, tid = make_bare_target()
    ctrl.step()
    threads = ctrl.deliberations.for_subject("node", tid)
    assert len(threads) == 1
    first = threads[0]["messages"][0]
    assert "do we already own the climbing boots?" in first["text"]
    packet = first["packet"]
    assert packet["checkpoint"] == "decomposition"
    assert {s["branch"] for s in packet["proposal"]["subtargets"]} == \
        {"buy", "have"}
    # nothing woven yet: consensus first
    assert ctrl.graph.by_kind(NodeKind.SUB_TARGET) == []


def test_resolving_the_thread_weaves_only_the_answered_branch():
    ctrl, tid = make_bare_target()
    ctrl.step()
    th = ctrl.deliberations.for_subject("node", tid)[0]
    ctrl.resolve_deliberation(th["id"], "modified", note="we need to buy",
                              changes={"branch": "buy"}, actor=Actor.HUMAN)
    subs = ctrl.graph.by_kind(NodeKind.SUB_TARGET)
    assert sorted(s["label"] for s in subs) == \
        ["find best buys", "purchase after consensus"]
    for s in subs:
        edges = [e for e in ctrl.graph.in_edges(tid) if e["src"] == s["id"]]
        assert edges and edges[0]["type"] == "SUPPORT"
    # the fed target is no longer a candidate; no duplicate threads either
    ctrl.step()
    assert len(ctrl.deliberations.for_subject("node", tid)) == 1


def test_one_thread_per_target_even_before_resolution():
    ctrl, tid = make_bare_target()
    ctrl.step()
    ctrl.step()
    assert len(ctrl.deliberations.for_subject("node", tid)) == 1


def test_scoping_conversation_refines_the_breakdown_on_reply():
    ctrl, tid = make_bare_target()
    ctrl.step()
    th = ctrl.deliberations.for_subject("node", tid)[0]
    # the owner answers WHERE they are going; the breakdown must adapt
    ctrl.reply_deliberation(th["id"], "vado sul K2", Actor.HUMAN)
    th = ctrl.deliberations.threads[th["id"]]
    latest = [m for m in th["messages"]
              if (m.get("packet") or {}).get("checkpoint") == "decomposition"][-1]
    labels = {s["label"] for s in latest["packet"]["proposal"]["subtargets"]}
    assert "hire a mountain guide" in labels and "obtain climbing permits" in labels
    # resolving now weaves the REFINED breakdown, not the opening one
    ctrl.resolve_deliberation(th["id"], "confirmed", note="ok",
                              actor=Actor.HUMAN)
    from pgdca.domain import NodeKind as NK
    subs = {s["label"] for s in ctrl.graph.by_kind(NK.SUB_TARGET)}
    assert "hire a mountain guide" in subs


def test_toy_world_targets_are_fed_and_never_decomposed():
    ctrl, _ = create()          # scripted mock adapter, mountain world
    ctrl.step()
    assert not any(
        (th["messages"][0].get("packet") or {}).get("checkpoint")
        == "decomposition" for th in ctrl.deliberations.snapshot())
