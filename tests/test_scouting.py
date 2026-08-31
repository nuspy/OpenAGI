"""Product scouting: a buy-target becomes real options -> owner's choice
-> a gated payment sub-target. Browser is a fake; no network, no money.
"""
from __future__ import annotations

from pgdca.cognition.gateway import SCHEMA_VERSION
from pgdca.domain import NodeKind
from pgdca.events import Actor
from pgdca.ports.browser import PageState
from pgdca.scenario.toy import create
from pgdca.tools.external import register_external_ports


class ScoutAdapter:
    """Scripted: search proposes a URL, extract proposes two options."""

    def generate(self, request):
        role = request.get("role")
        ctx = request.get("context", {})
        if role == "scout" and ctx.get("phase") == "search":
            return {"schema": SCHEMA_VERSION, "role": role, "summary": "search",
                    "hypotheses": [{"action_name": "search_web", "params": {
                        "url": "https://shop.test/boots"}}]}
        if role == "scout" and ctx.get("phase") == "extract":
            assert ctx.get("pages"), "extract must receive fetched pages"
            return {"schema": SCHEMA_VERSION, "role": role, "summary": "opts",
                    "hypotheses": [
                        {"action_name": "propose_option", "params": {
                            "label": "La Sportiva Trango", "price": 280,
                            "currency": "EUR", "merchant": "AlpineShop",
                            "url": "https://shop.test/trango",
                            "characteristics": "B2, crampon-compatible"},
                         "rationale": "robusti per alta quota"},
                        {"action_name": "propose_option", "params": {
                            "label": "Scarpa Charmoz", "price": 210,
                            "currency": "EUR", "merchant": "AlpineShop",
                            "characteristics": "B1, trekking"},
                         "rationale": "piu' economici"}]}
        return {"schema": SCHEMA_VERSION, "role": role or "?",
                "summary": "no-op", "hypotheses": []}


class FakeBrowser:
    def navigate(self, url):
        return PageState(url=url, title="Boots", content_excerpt="Trango 280 EUR")

    def extract(self, selector=None):
        return {"url": "x", "text": "y", "trust": "untrusted"}


def setup():
    ctrl, _ = create(adapter=ScoutAdapter(), build=False)
    register_external_ports(ctrl.registry, browser=FakeBrowser())
    tid = ctrl.propose_goal(NodeKind.TARGET, "find best buys: climbing boots",
                            0.9, Actor.HUMAN)
    ctrl.ratify_goal(tid, Actor.HUMAN)
    return ctrl, tid


def test_scouting_opens_option_cards():
    ctrl, tid = setup()
    ctrl.scouting.step()
    th = ctrl.deliberations.for_subject("node", tid)
    assert len(th) == 1
    pk = th[0]["messages"][0]["packet"]
    assert pk["checkpoint"] == "scouting"
    opts = pk["options"]
    assert [o["label"] for o in opts] == ["La Sportiva Trango", "Scarpa Charmoz"]
    assert all(o["trust"] == "untrusted" for o in opts)


def test_choosing_weaves_a_gated_payment_subtarget():
    ctrl, tid = setup()
    ctrl.scouting.step()
    th = ctrl.deliberations.for_subject("node", tid)[0]
    ctrl.resolve_deliberation(th["id"], "modified", note="prendo i Trango",
                              changes={"chosen": 0}, actor=Actor.HUMAN)
    paid = [n for n in ctrl.graph.by_kind(NodeKind.SUB_TARGET)
            if n["props"].get("intent") == "pay"]
    assert len(paid) == 1
    p = paid[0]["props"]
    assert p["merchant"] == "AlpineShop" and p["amount"] == 280
    assert "Trango" in paid[0]["label"]


def test_no_browser_no_scouting():
    ctrl, _ = create(adapter=ScoutAdapter(), build=False)
    tid = ctrl.propose_goal(NodeKind.TARGET, "buy climbing boots", 0.9,
                            Actor.HUMAN)
    ctrl.ratify_goal(tid, Actor.HUMAN)
    assert ctrl.scouting.step() == []          # browser tool not enabled
